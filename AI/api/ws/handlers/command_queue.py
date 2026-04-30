# -*- coding: utf-8 -*-
"""
Command queue manager: serialize command/response batches per session.
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Callable

from core.interfaces import MCPCommand

logger = logging.getLogger(__name__)


@dataclass
class CommandBatch:
    session_id: str
    commands: List[MCPCommand]
    response_text: str
    current_url: str
    pending: Dict[str, int] = field(default_factory=dict)
    tts_pending: bool = False
    created_at: float = field(default_factory=time.time)
    done: asyncio.Event = field(default_factory=asyncio.Event)


class CommandQueueManager:
    """
    Ensures command/response batches are executed in order per session.

    Completion = all pending tool results received AND TTS finished.
    """

    def __init__(self, sender):
        self._sender = sender
        self._queues: Dict[str, Deque[CommandBatch]] = {}
        self._active: Dict[str, CommandBatch] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    def create_session(self, session_id: str) -> None:
        self._queues.setdefault(session_id, deque())

    def cleanup_session(self, session_id: str) -> None:
        self.interrupt(session_id)
        self._queues.pop(session_id, None)

    def interrupt(self, session_id: str) -> None:
        queue = self._queues.get(session_id)
        if queue is not None:
            for batch in list(queue):
                batch.done.set()
            queue.clear()
        active = self._active.pop(session_id, None)
        if active:
            active.done.set()
        task = self._tasks.pop(session_id, None)
        if task:
            task.cancel()

    async def enqueue_batch(
        self,
        session_id: str,
        commands: List[MCPCommand],
        response_text: str,
        current_url: str,
        interrupted: Optional[Callable[[], bool]] = None,
        front: bool = False,
        wait: bool = True,
    ) -> Optional[str]:
        if interrupted and interrupted():
            return None

        if not commands and not response_text:
            return None

        self._queues.setdefault(session_id, deque())
        batch = CommandBatch(
            session_id=session_id,
            commands=commands or [],
            response_text=response_text or "",
            current_url=current_url or "",
        )
        if front:
            self._queues[session_id].appendleft(batch)
        else:
            self._queues[session_id].append(batch)
        if session_id not in self._active:
            await self._start_next(session_id)
        if wait:
            await self._wait_for_completion(batch)
        return response_text or None

    async def handle_mcp_result(self, session_id: str, tool_name: str, arguments: Optional[dict]) -> bool:
        batch = self._active.get(session_id)
        if not batch:
            return False
        if not tool_name:
            return False
        if tool_name.startswith("extract"):
            return False

        # MCP can occasionally send arguments as a JSON string. Normalize so our
        # fingerprint matches what we originally dispatched.
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)  # type: ignore[assignment]
            except Exception:
                arguments = {}

        key = _fingerprint(tool_name, arguments or {})
        if key not in batch.pending:
            fallback_key = _resolve_fallback_key(batch.pending, tool_name, arguments)
            if not fallback_key:
                return False
            key = fallback_key

        batch.pending[key] -= 1
        if batch.pending[key] <= 0:
            batch.pending.pop(key, None)
        logger.info(
            "Command queue progress: session=%s tool=%s pending=%d",
            session_id,
            tool_name,
            sum(batch.pending.values()),
        )
        await self._maybe_finish(session_id)
        return True

    async def _start_next(self, session_id: str) -> None:
        if session_id in self._active:
            return
        queue = self._queues.get(session_id)
        if not queue:
            return
        batch = queue.popleft()
        self._active[session_id] = batch
        logger.info(
            "Command queue start: session=%s commands=%d tts=%s",
            session_id,
            len(batch.commands or []),
            bool(batch.response_text),
        )
        task = asyncio.create_task(self._dispatch_batch(session_id, batch))
        self._tasks[session_id] = task

    async def _dispatch_batch(self, session_id: str, batch: CommandBatch) -> None:
        try:
            if batch.commands:
                batch.pending = _build_pending(batch.commands)
                await self._sender.send_tool_calls(session_id, batch.commands)
            if batch.response_text:
                batch.tts_pending = True
                await self._sender.send_tts_response(session_id, batch.response_text)
                batch.tts_pending = False
                await self._maybe_finish(session_id)
            else:
                await self._maybe_finish(session_id)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error("Command batch dispatch failed: session=%s error=%s", session_id, e)
            # Ensure we don't block the queue forever
            self._active.pop(session_id, None)
            self._tasks.pop(session_id, None)
            await self._start_next(session_id)

    async def _maybe_finish(self, session_id: str) -> None:
        batch = self._active.get(session_id)
        if not batch:
            return
        if batch.pending:
            return
        if batch.tts_pending:
            return

        self._active.pop(session_id, None)
        self._tasks.pop(session_id, None)
        batch.done.set()
        logger.info("Command queue complete: session=%s", session_id)
        await self._start_next(session_id)

    async def _wait_for_completion(self, batch: CommandBatch) -> None:
        timeout = _get_wait_timeout()
        try:
            if timeout:
                await asyncio.wait_for(batch.done.wait(), timeout)
            else:
                await batch.done.wait()
        except asyncio.TimeoutError:
            logger.warning(
                "Command queue timeout: session=%s commands=%d tts=%s",
                batch.session_id,
                len(batch.commands or []),
                bool(batch.response_text),
            )
            batch.done.set()


def _build_pending(commands: List[MCPCommand]) -> Dict[str, int]:
    pending: Dict[str, int] = {}
    for cmd in commands:
        tool_name = getattr(cmd, "tool_name", "") or ""
        if tool_name.startswith("extract"):
            continue
        key = _fingerprint(tool_name, getattr(cmd, "arguments", None) or {})
        pending[key] = pending.get(key, 0) + 1
    return pending


def _fingerprint(tool_name: str, arguments: dict) -> str:
    try:
        payload = json.dumps(arguments, sort_keys=True, ensure_ascii=True)
    except Exception:
        payload = str(arguments)
    return f"{tool_name}:{payload}"


def _resolve_fallback_key(pending: Dict[str, int], tool_name: str, arguments: Optional[dict]) -> Optional[str]:
    """
    MCP 결과에 arguments가 누락되는 경우를 대비한 폴백 매칭.

    동일 tool_name에 대해 pending이 1개뿐일 때만 매칭한다.
    """
    if arguments:
        return None
    prefix = f"{tool_name}:"
    candidates = [key for key in pending.keys() if key.startswith(prefix)]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _get_wait_timeout() -> float:
    raw = os.getenv("COMMAND_QUEUE_WAIT_TIMEOUT_SEC", "120").strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 120.0
