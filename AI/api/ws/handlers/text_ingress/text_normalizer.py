# -*- coding: utf-8 -*-
"""
Text normalization helpers for user input.
"""


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.strip().split())
