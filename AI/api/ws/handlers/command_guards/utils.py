# -*- coding: utf-8 -*-
"""
Shared helpers for command guards.
"""

from __future__ import annotations


def get_tool_name(cmd) -> str:
    if hasattr(cmd, "tool_name"):
        return cmd.tool_name or ""
    if isinstance(cmd, dict):
        return cmd.get("tool_name", "") or ""
    return ""


def get_args(cmd) -> dict:
    if hasattr(cmd, "arguments"):
        return cmd.arguments or {}
    if isinstance(cmd, dict):
        return cmd.get("arguments", {}) or {}
    return {}


def compact_text(value: str) -> str:
    if not value:
        return ""
    # Remove all whitespace to make text matching resilient.
    return "".join(str(value).split())


__all__ = ["get_tool_name", "get_args", "compact_text"]

