# -*- coding: utf-8 -*-

from datetime import date, datetime

from core.korean_datetime import format_date_for_tts


def test_format_date_for_tts_parses_common_ymd_strings() -> None:
    assert format_date_for_tts("2026-02-06") == "2026년 2월 6일"
    assert format_date_for_tts("2025.02.04") == "2025년 2월 4일"
    assert format_date_for_tts("2026/2/6") == "2026년 2월 6일"
    assert format_date_for_tts("  2026-02-06  ") == "2026년 2월 6일"


def test_format_date_for_tts_drops_time_portion() -> None:
    assert format_date_for_tts("2026-02-06T12:34:56") == "2026년 2월 6일"
    assert format_date_for_tts("2026-02-06 12:34:56") == "2026년 2월 6일"


def test_format_date_for_tts_handles_date_objects() -> None:
    assert format_date_for_tts(date(2026, 2, 6)) == "2026년 2월 6일"
    assert format_date_for_tts(datetime(2026, 2, 6, 12, 34, 56)) == "2026년 2월 6일"

