# -*- coding: utf-8 -*-
"""
Flow handler for active flow steps.
"""


class FlowHandler:
    def __init__(self, flow_engine, sender):
        self._flow = flow_engine
        self._sender = sender

    def is_flow_active(self, session_id: str) -> bool:
        if not self._flow:
            return False
        return self._flow.is_flow_active(session_id)

    async def handle_flow_input(self, session_id: str, text: str, session) -> None:
        if not self._flow or not session:
            return
        user_input = {"text": text}
        next_step = await self._flow.next_step(session, user_input)
        await self._sender.send_flow_step(session_id, next_step)
        if next_step.prompt:
            await self._sender.send_tts_response(session_id, next_step.prompt)
