# -*- coding: utf-8 -*-
"""
LLM response parser and validator.
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from ..context.context_rules import GeneratedCommand
from .llm_logging import truncate
from services.llm.errors.llm_errors import LLMParseError

logger = logging.getLogger(__name__)


@dataclass
class ParsedResponse:
    commands: List[GeneratedCommand]
    response_text: str
    success: bool = True
    error: Optional[str] = None


class LLMResponseParser:
    """Parse JSON content into commands and response text."""

    def __init__(self, normalizer):
        self._normalizer = normalizer

    def parse(self, content: str, current_url: str = "") -> ParsedResponse:
        try:
            data = json.loads(content)

            # data가 dict가 아니면 파싱 실패로 처리
            if not isinstance(data, dict):
                logger.error(
                    "LLM response is not a dict: type=%s content=%s",
                    type(data).__name__,
                    truncate(content),
                )
                raise LLMParseError(
                    "invalid_response_type",
                    f"LLM 응답이 dict가 아닙니다: {type(data).__name__}",
                )

            response_text = data.get("response", "")
            if isinstance(response_text, str):
                response_text = response_text.strip()
            else:
                response_text = str(response_text)

            commands_data = data.get("commands")
            if commands_data is None:
                commands_data = data.get("tool_calls")
                if commands_data is None:
                    commands_data = data.get("actions")
            if commands_data is None:
                logger.warning(
                    "LLM response missing commands/tool_calls. keys=%s content=%s",
                    list(data.keys()),
                    truncate(content)
                )
                commands_data = []

            if not response_text or len(response_text) < 5:
                details = data.get("details")
                if isinstance(details, dict) and details:
                    response_text = self._format_details(details)

            commands: List[GeneratedCommand] = []
            for cmd in commands_data:
                if not isinstance(cmd, dict):
                    logger.warning("Skipping non-dict command: %s", cmd)
                    continue
                action = (
                    cmd.get("tool_name")
                    or cmd.get("action")
                    or cmd.get("tool")
                    or ""
                )
                args = cmd.get("arguments") or cmd.get("args") or {}
                desc = cmd.get("description") or cmd.get("desc") or ""

                action, args = self._normalizer.normalize(action, args, current_url)

                if self._validate_command(action, args):
                    commands.append(GeneratedCommand(
                        tool_name=action,
                        arguments=args,
                        description=desc
                    ))
                else:
                    logger.warning(f"유효하지 않은 명령 무시: {cmd}")

            result = ParsedResponse(
                commands=commands,
                response_text=response_text,
                success=True
            )
            if not commands:
                logger.warning(
                    "LLM produced no commands. response_text=%s content=%s",
                    truncate(response_text),
                    truncate(content)
                )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}, content: {content[:200]}")
            raise LLMParseError("json_parse", f"JSON 파싱 실패: {e}", e)

    def _format_details(self, details: Dict[str, Any]) -> str:
        lines = ["상품 정보 안내입니다."]
        for key, value in details.items():
            if isinstance(value, dict):
                lines.append(f"- {key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  - {sub_key}: {sub_value}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _validate_command(self, action: str, args: Dict[str, Any]) -> bool:
        valid_actions = [
            "goto",
            "click",
            "fill",
            "press",
            "wait",
            "click_text",
            "scroll",
            "extract",
            "extract_cart",
            "extract_order_list",
            "extract_detail",
            "extract_order_detail",
            "get_visible_buttons",
            "get_text",
            "get_pages",
            "navigate_to_url",
            "click_element",
            "fill_input",
            "press_key",
            "take_screenshot",
            "wait_for_new_page",
            "wait_for_selector",
        ]

        if action not in valid_actions:
            return False

        if action == "goto" and "url" not in args:
            return False
        if action == "click" and "selector" not in args:
            return False
        if action == "fill" and ("selector" not in args or "text" not in args):
            return False
        if action == "click_text" and "text" not in args:
            return False
        if action == "extract" and "selector" not in args:
            return False
        if action == "extract_detail":
            return True
        if action == "get_text" and "selector" not in args:
            return False
        if action == "click_element" and "selector" not in args:
            return False
        if action == "fill_input" and ("selector" not in args or "value" not in args):
            return False
        if action == "press_key" and "selector" not in args:
            return False

        return True
