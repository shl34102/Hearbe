"""
Shared MCP tool helpers (alias/args normalization, frame context resolution).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

from playwright.async_api import Page, Frame, FrameLocator


TOOL_ALIAS_MAP = {
    "goto": "navigate_to_url",
    "click": "click_element",
    "fill": "fill_input",
    "press": "press_key",
    "screenshot": "take_screenshot",
}


def normalize_tool_call(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    tool = TOOL_ALIAS_MAP.get(tool_name, tool_name)
    args: Dict[str, Any] = dict(arguments or {})

    if tool == "fill_input" and "text" in args and "value" not in args:
        args["value"] = args.pop("text")
    if tool == "click_element" and "timeout" in args and "wait_timeout" not in args:
        args["wait_timeout"] = args.pop("timeout")

    return tool, args


def resolve_frame_context(
    page: Page,
    frame_selector: Optional[str] = None,
    frame_name: Optional[str] = None,
    frame_url: Optional[str] = None,
    frame_index: Optional[int] = None,
) -> Tuple[str, Union[Page, Frame, FrameLocator], Optional[str]]:
    if frame_selector:
        return "frame_locator", page.frame_locator(frame_selector), None

    if frame_name or frame_url:
        frame = page.frame(name=frame_name, url=frame_url)
        if not frame:
            return "page", page, "Frame not found"
        return "frame", frame, None

    if frame_index is not None:
        try:
            index = int(frame_index)
        except (TypeError, ValueError):
            return "page", page, "Invalid frame_index"
        frames = page.frames
        if index < 0 or index >= len(frames):
            return "page", page, "Frame index out of range"
        return "frame", frames[index], None

    return "page", page, None
