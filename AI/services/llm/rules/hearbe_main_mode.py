# -*- coding: utf-8 -*-
"""
Hearbe /main mode selection rule (deterministic).

This handles voice intents for common/sharing/big/audio mode selection on the Hearbe /main page.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from . import BaseRule, RuleResult
from ..context.context_rules import GeneratedCommand, build_goto_command, build_wait_command
from ..sites.site_manager import get_current_site, get_page_type

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip()


def _is_hearbe_site(current_url: str, current_site) -> bool:
    if current_site and getattr(current_site, "site_id", "") == "hearbe":
        return True
    site = get_current_site(current_url) if current_url else None
    return bool(site and getattr(site, "site_id", "") == "hearbe")


def _get_base_url(current_url: str, current_site) -> Optional[str]:
    if current_url:
        try:
            parsed = urlparse(current_url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass

    if current_site:
        base_source = current_site.get_url("home") or current_site.get_url("intro")
        if not base_source and getattr(current_site, "urls", None):
            try:
                base_source = next(iter(current_site.urls.values()))
            except Exception:
                base_source = None
        if base_source:
            try:
                parsed = urlparse(base_source)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

    return None


# Triggers include Korean and English (UTF-8).
_TRIG_COMMON = (
    "일반",
    "일반 쇼핑",
    "일반쇼핑",
    "일반 모드",
    "일반모드",
)

_TRIG_TYPE_A = (
    "a형",
    "a 타입",
    "a타입",
    "type a",
    "typea",
    "에이형",
    "에이 형",
    "에이 타입",
    "에이타입",
    "타입 a",
    "타입a",
    "음성 큰글씨",
    "음성큰글씨",
    "음성 큰 글씨",
    "음성큰 글씨",
)

_TRIG_TYPE_B = (
    "b형",
    "b 타입",
    "b타입",
    "type b",
    "typeb",
    "비형",
    "비 형",
    "비 타입",
    "비타입",
    "타입 b",
    "타입b",
    "고대비",
    "고대비 쇼핑",
    "고대비쇼핑",
)

_TRIG_TYPE_C = (
    "c형",
    "c 타입",
    "c타입",
    "type c",
    "typec",
    "씨형",
    "씨 형",
    "씨 타입",
    "씨타입",
    "타입 c",
    "타입c",
)
_TRIG_SHARING = (
    "공유",
    "공유 쇼핑",
    "공유쇼핑",
    "공유 모드",
    "공유모드",
)
_TRIG_BIG = (
    "큰 글씨",
    "큰글씨",
    "큰 글씨 쇼핑",
    "큰글씨쇼핑",
    "큰 글씨 모드",
    "큰글씨모드",
)
_TRIG_AUDIO = (
    "음성",
    "음성 안내",
    "음성안내",
    "음성 안내 쇼핑",
    "음성안내쇼핑",
    "음성 모드",
    "음성모드",
)

_OPTIONS = [
    (_TRIG_TYPE_A, "/spline-test", "A형(음성 큰글씨 쇼핑)으로 이동합니다.", "hearbe_main_mode_type_a"),
    (_TRIG_TYPE_B, "/B/login", "B형(고대비 쇼핑)으로 이동합니다.", "hearbe_main_mode_type_b"),
    (_TRIG_TYPE_C, "/C/login", "C형(일반 쇼핑)으로 이동합니다.", "hearbe_main_mode_type_c"),
    (_TRIG_COMMON, "/C/login", "일반 쇼핑으로 이동합니다.", "hearbe_main_mode_common"),
    (_TRIG_SHARING, "/S/join", "공유 쇼핑으로 이동합니다.", "hearbe_main_mode_sharing"),
    (_TRIG_BIG, "/A/login", "큰 글씨 쇼핑으로 이동합니다.", "hearbe_main_mode_big"),
    (_TRIG_AUDIO, "/spline-test", "음성 안내 쇼핑으로 이동합니다.", "hearbe_main_mode_audio"),
]


class HearbeMainModeRule(BaseRule):
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not _is_hearbe_site(current_url, current_site):
            return None
        if get_page_type(current_url) != "main":
            return None

        norm = _normalize(text)
        if not norm:
            return None
        lowered = norm.lower()
        compact = lowered.replace(" ", "")

        base_url = _get_base_url(current_url, current_site)
        if not base_url:
            return None

        selected = None
        for triggers, path, response_text, rule_name in _OPTIONS:
            for t in triggers:
                if t and (t in lowered or t.replace(" ", "") in compact):
                    selected = (path, response_text, rule_name)
                    break
            if selected:
                break
        if not selected:
            return None

        path, response_text, rule_name = selected
        target_url = f"{base_url}{path}"
        commands: list[GeneratedCommand] = [
            build_goto_command(target_url, f"Hearbe mode select: {path}"),
            build_wait_command(1200, "Page load wait"),
        ]
        return RuleResult(
            matched=True,
            commands=commands,
            response_text=response_text,
            rule_name=rule_name,
        )


__all__ = ["HearbeMainModeRule"]
