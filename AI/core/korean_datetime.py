# -*- coding: utf-8 -*-
"""
Korean-friendly datetime formatting helpers.

These helpers are used to generate natural spoken Korean strings for TTS.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Optional


_DATE_YMD_RE = re.compile(r"^\s*(\d{4})[.\-\/](\d{1,2})[.\-\/](\d{1,2})\s*$")
_DATE_MD_RE = re.compile(r"^\s*(\d{1,2})[.\-\/](\d{1,2})\s*$")
_DIGITS_ONLY_RE = re.compile(r"^\s*\d+\s*$")


def format_date_for_tts(value: Any) -> str:
    """
    Format common date representations into a natural Korean spoken form.

    Examples:
      - "2026-02-06" -> "2026년 2월 6일"
      - "2025.02.04" -> "2025년 2월 4일"
      - "2026-02-06T12:34:56" -> "2026년 2월 6일"

    When parsing fails, returns the original string (trimmed).
    """
    if value is None:
        return ""

    if isinstance(value, datetime):
        d = value.date()
        return f"{d.year}년 {d.month}월 {d.day}일"
    if isinstance(value, date):
        return f"{value.year}년 {value.month}월 {value.day}일"

    s = str(value).strip()
    if not s:
        return ""

    # Drop time portion if present.
    for sep in ("T", " "):
        if sep in s:
            s = s.split(sep, 1)[0].strip()

    # Epoch timestamps (seconds or milliseconds).
    # Keep this best-effort and safe: only act on digits-only values.
    if _DIGITS_ONLY_RE.match(s):
        ts = _parse_epoch_timestamp(s)
        if ts:
            d = ts.date()
            return f"{d.year}년 {d.month}월 {d.day}일"

    # YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD
    m = _DATE_YMD_RE.match(s)
    if m:
        y, mo, d = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y}년 {mo}월 {d}일"

    # MM-DD (rare, but better than raw)
    m = _DATE_MD_RE.match(s)
    if m:
        mo, d = (int(m.group(1)), int(m.group(2)))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{mo}월 {d}일"

    return s


def _parse_epoch_timestamp(value: str) -> Optional[datetime]:
    value = str(value).strip()
    if not value or not value.isdigit():
        return None
    # 13 digits: ms, 10 digits: sec
    try:
        if len(value) == 13:
            ms = int(value)
            return datetime.fromtimestamp(ms / 1000.0, tz=_get_kst_fallback())
        if len(value) == 10:
            sec = int(value)
            return datetime.fromtimestamp(sec, tz=_get_kst_fallback())
    except Exception:
        return None
    return None


def _get_kst_fallback() -> timezone:
    """
    Best-effort KST timezone.

    On Windows, zoneinfo may not have IANA database; fall back to UTC
    (date still usually correct for midnight-ish timestamps).
    """
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+

        return ZoneInfo("Asia/Seoul")
    except Exception:
        return timezone.utc


__all__ = ["format_date_for_tts"]

