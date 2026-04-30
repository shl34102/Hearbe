# -*- coding: utf-8 -*-
"""
Login TTS page module.
"""

from typing import Optional

from api.ws.presenter.pages.login import (
    build_login_success_tts as _build_success,
    build_login_autofill_success_tts as _build_autofill_success,
    build_login_guidance_tts as _build_guidance,
    build_captcha_prompt_tts as _build_captcha,
)


def build_login_success_tts(current_url: str) -> str:
    return _build_success(current_url)


def build_login_autofill_success_tts(current_url: str) -> str:
    return _build_autofill_success(current_url)


def build_login_guidance_tts(active_method: Optional[str] = None) -> str:
    return _build_guidance(active_method)


def build_captcha_prompt_tts() -> str:
    return _build_captcha()
