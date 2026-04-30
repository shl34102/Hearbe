"""
LLM debug logging helpers.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


_DEBUG_ENABLED = os.environ.get("LLM_DEBUG_LOG", "false").lower() in ("1", "true", "yes", "y")


def is_debug_enabled() -> bool:
    return _DEBUG_ENABLED


def truncate(text: Optional[str], limit: int = 400) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


def redact_messages(messages: List[Dict[str, str]], limit: int = 400) -> List[Dict[str, str]]:
    redacted: List[Dict[str, str]] = []
    for msg in messages:
        content = msg.get("content", "")
        redacted.append(
            {
                "role": msg.get("role", "user"),
                "content": truncate(content, limit=limit),
            }
        )
    return redacted


def log_llm_request(
    logger,
    model: str,
    base_url: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    response_format: Optional[Dict[str, Any]],
    token_param: str,
) -> None:
    if not _DEBUG_ENABLED:
        return
    payload = {
        "model": model,
        "base_url": base_url,
        token_param: max_tokens,
        "messages": redact_messages(messages),
    }
    if response_format:
        payload["response_format"] = response_format
    logger.info(
        "LLM request payload: %s",
        json.dumps(
            payload,
            ensure_ascii=True,
        ),
    )


def log_llm_response(logger, response, content: Optional[str]) -> None:
    if not _DEBUG_ENABLED:
        return
    finish_reason = None
    if getattr(response, "choices", None):
        finish_reason = response.choices[0].finish_reason
    logger.info(
        "LLM response payload: %s",
        json.dumps(
            {
                "model": getattr(response, "model", None),
                "id": getattr(response, "id", None),
                "finish_reason": finish_reason,
                "content": truncate(content),
            },
            ensure_ascii=True,
        ),
    )
