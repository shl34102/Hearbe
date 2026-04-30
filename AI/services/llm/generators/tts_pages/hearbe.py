# -*- coding: utf-8 -*-
"""
Hearbe TTS page module.
"""

from api.ws.presenter.pages.hearbe import (
    build_hearbe_login_redirect_tts as _build_login_redirect,
    build_hearbe_main_guidance_tts as _build_main_guidance,
    build_hearbe_mall_guidance_tts as _build_mall_guidance,
)


def build_hearbe_main_guidance_tts() -> str:
    return _build_main_guidance()


def build_hearbe_login_redirect_tts() -> str:
    return _build_login_redirect()


def build_hearbe_mall_guidance_tts() -> str:
    return _build_mall_guidance()


__all__ = [
    "build_hearbe_main_guidance_tts",
    "build_hearbe_login_redirect_tts",
    "build_hearbe_mall_guidance_tts",
]
