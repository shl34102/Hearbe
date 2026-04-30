"""
Available command specifications for LLM prompt construction.
"""

from typing import Dict, Any


AVAILABLE_COMMANDS: Dict[str, Dict[str, Any]] = {
    "goto": {
        "description": "Navigate to a URL",
        "args": {"url": "Destination URL"},
        "example": (
            '{"tool_name": "goto", "arguments": {"url": "https://www.coupang.com/"}, '
            '"description": "Go to Coupang"}'
        ),
    },
    "click": {
        "description": "Click an element by CSS selector",
        "args": {
            "selector": "CSS selector",
            "frame_selector": "iframe CSS selector (optional)",
        },
        "example": (
            '{"tool_name": "click", "arguments": {"selector": "#login-btn"}, '
            '"description": "Click login button"}'
        ),
    },
    "fill": {
        "description": "Fill text into an input",
        "args": {
            "selector": "CSS selector",
            "text": "Text to input",
            "frame_selector": "iframe CSS selector (optional)",
        },
        "example": (
            '{"tool_name": "fill", "arguments": {"selector": "input[name=q]", "text": "ramen"}, '
            '"description": "Type search keyword"}'
        ),
    },
    "press": {
        "description": "Press a key in an input",
        "args": {
            "selector": "CSS selector",
            "key": "Key name (Enter, Tab, etc.)",
            "frame_selector": "iframe CSS selector (optional)",
        },
        "example": (
            '{"tool_name": "press", "arguments": {"selector": "input", "key": "Enter"}, '
            '"description": "Submit input"}'
        ),
    },
    "wait": {
        "description": "Wait for a given time",
        "args": {"ms": "Milliseconds"},
        "example": (
            '{"tool_name": "wait", "arguments": {"ms": 1000}, "description": "Wait 1 second"}'
        ),
    },
    "click_text": {
        "description": "Find and click by visible text",
        "args": {"text": "Text to match"},
        "example": (
            '{"tool_name": "click_text", "arguments": {"text": "Cart"}, '
            '"description": "Click text"}'
        ),
    },
    "scroll": {
        "description": "Scroll the page",
        "args": {"direction": "up or down", "amount": "Pixels (optional)"},
        "example": (
            '{"tool_name": "scroll", "arguments": {"direction": "down", "amount": 500}, '
            '"description": "Scroll down"}'
        ),
    },
    "extract_order_list": {
        "description": "Extract order list items",
        "args": {},
        "example": (
            '{"tool_name": "extract_order_list", "arguments": {}, '
            '"description": "Extract order list"}'
        ),
    },
    "get_text": {
        "description": "Get text content from an element",
        "args": {
            "selector": "CSS selector",
            "frame_selector": "iframe CSS selector (optional)",
            "frame_name": "iframe name (optional)",
            "frame_url": "iframe URL match (optional)",
            "frame_index": "iframe index (optional)",
        },
        "example": (
            '{"tool_name": "get_text", "arguments": {"selector": ".total-price"}, '
            '"description": "Read total price"}'
        ),
    },
    "get_visible_buttons": {
        "description": "Get visible clickable buttons on the page",
        "args": {"max_items": "Max number of buttons (optional)"},
        "example": (
            '{"tool_name": "get_visible_buttons", "arguments": {"max_items": 200}, '
            '"description": "List visible buttons"}'
        ),
    },
    "get_pages": {
        "description": "List open browser pages/tabs",
        "args": {},
        "example": (
            '{"tool_name": "get_pages", "arguments": {}, "description": "List open tabs"}'
        ),
    },
    "take_screenshot": {
        "description": "Capture a screenshot",
        "args": {"full_page": "Capture full page if true (optional)"},
        "example": (
            '{"tool_name": "take_screenshot", "arguments": {"full_page": true}, '
            '"description": "Capture full page screenshot"}'
        ),
    },
    "wait_for_new_page": {
        "description": "Wait for a new tab/page and optionally focus it",
        "args": {"timeout_ms": "Timeout in ms (optional)", "focus": "Focus new page if true (optional)"},
        "example": (
            '{"tool_name": "wait_for_new_page", "arguments": {"timeout_ms": 1500, "focus": true}, '
            '"description": "Wait for new page and focus"}'
        ),
    },
    "wait_for_selector": {
        "description": "Wait for a selector to reach a state (visible by default)",
        "args": {
            "selector": "CSS selector",
            "state": "attached|detached|visible|hidden (optional)",
            "timeout": "Timeout in ms (optional)",
            "frame_selector": "iframe CSS selector (optional)",
        },
        "example": (
            '{"tool_name": "wait_for_selector", "arguments": {"selector": "input._phoneInput", '
            '"state": "visible", "timeout": 8000}, "description": "Wait for phone input"}'
        ),
    },
    "handle_captcha_modal": {
        "description": "Detect captcha modal and click audio button if present",
        "args": {},
        "example": (
            '{"tool_name": "handle_captcha_modal", "arguments": {}, '
            '"description": "Handle captcha modal if present"}'
        ),
    },
}
