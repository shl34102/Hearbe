# -*- coding: utf-8 -*-
"""
Welfare card OCR parser.

Runs PaddleOCR on uploaded card images and extracts fields used for
registration auto-fill assistance.
"""

import io
import logging
import re
import threading
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

from services.ocr.text_processors.korean_ocr import (
    create_ocr_instance,
    extract_texts_with_scores,
)

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 50 * 1024 * 1024

_OCR_LOCK = threading.Lock()
_OCR_INSTANCES: Dict[str, Any] = {}

_COMPANY_ALIASES: Dict[str, Sequence[str]] = {
    "KB국민카드": ("KB국민", "국민카드", "KBCARD"),
    "신한카드": ("신한카드", "신한", "SHINHAN"),
    "삼성카드": ("삼성카드", "삼성", "SAMSUNG"),
    "현대카드": ("현대카드", "현대", "HYUNDAI"),
    "롯데카드": ("롯데카드", "롯데", "LOTTE"),
    "우리카드": ("우리카드", "우리", "WOORI"),
    "하나카드": ("하나카드", "하나", "HANA"),
    "NH농협카드": ("농협카드", "NH농협", "NHCARD"),
    "IBK기업카드": ("기업카드", "IBK", "기업은행"),
    "BC카드": ("BC카드", "BCCARD", "비씨카드"),
}

_CARD_NUMBER_PATTERN = re.compile(r"(?<!\d)(\d[\d\-\s]{12,28}\d)(?!\d)")
_EXP_PATTERN = re.compile(r"(?<!\d)(0?[1-9]|1[0-2])\s*[/\-.]\s*(\d{2,4})(?!\d)")
_EXP_COMPACT_PATTERN = re.compile(r"(?<!\d)(0[1-9]|1[0-2])\s*(\d{2})(?!\d)")
_CVC_CONTEXT_PATTERN = re.compile(
    r"(?:CVC|CVV|CID|CVC2|보안코드|안전코드|인증번호|검증번호)[^\d]{0,6}(\d{3,4})",
    re.IGNORECASE,
)

_EXPIRY_HINTS = ("EXP", "VALID", "THRU", "MMYY", "유효", "만료", "기한")
_CVC_HINTS = ("CVC", "CVV", "CID", "보안코드", "안전코드", "인증번호", "검증번호")


def extract_welfare_card_fields(image_data: bytes, device: str = "cpu") -> Dict[str, Any]:
    """
    Extract welfare card fields from image bytes.

    Returns:
        {
            "card_company": str | None,
            "card_number": str | None,
            "expiration_date": str | None,  # MM/YY
            "cvc": str | None,
            "confidence": {...},
            "raw_text": [...]
        }
    """
    lines, used_device = _run_ocr_with_fallback(image_data, device=device)
    raw_text = [text for text, _ in lines]

    company, company_conf = _extract_company(lines)
    card_number, card_number_conf = _extract_card_number(lines)
    expiration_date, expiration_conf = _extract_expiration_date(lines)
    cvc, cvc_conf = _extract_cvc(lines, card_number=card_number, expiration_date=expiration_date)

    logger.info(
        "Welfare card OCR extracted: device=%s company=%s card_number=%s exp=%s cvc=%s",
        used_device,
        bool(company),
        bool(card_number),
        bool(expiration_date),
        bool(cvc),
    )

    return {
        "card_company": company,
        "card_number": card_number,
        "expiration_date": expiration_date,
        "cvc": cvc,
        "confidence": {
            "card_company": company_conf,
            "card_number": card_number_conf,
            "expiration_date": expiration_conf,
            "cvc": cvc_conf,
        },
        "raw_text": raw_text,
    }


def _run_ocr_with_fallback(image_data: bytes, device: str) -> Tuple[List[Tuple[str, float]], str]:
    preferred = _normalize_device(device)
    candidates = [preferred]
    if preferred.startswith("gpu"):
        candidates.append("cpu")

    tried = set()
    last_error: Optional[Exception] = None

    for candidate in candidates:
        if candidate in tried:
            continue
        tried.add(candidate)

        try:
            return _run_ocr(image_data, candidate), candidate
        except Exception as e:
            last_error = e
            logger.warning("Welfare OCR failed on device=%s: %s", candidate, e)

    if last_error is not None:
        raise last_error
    raise RuntimeError("OCR execution failed without a specific error")


def _run_ocr(image_data: bytes, device: str) -> List[Tuple[str, float]]:
    if not image_data:
        raise ValueError("Empty image data")
    if len(image_data) > MAX_IMAGE_BYTES:
        raise ValueError("Image is too large")

    try:
        with Image.open(io.BytesIO(image_data)) as image:
            if image.mode != "RGB":
                image = image.convert("RGB")
            image_array = np.array(image)[:, :, ::-1]  # RGB -> BGR
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError("Invalid image format") from e

    with _OCR_LOCK:
        ocr = _OCR_INSTANCES.get(device)
        if ocr is None:
            ocr = create_ocr_instance(device=device)
            _OCR_INSTANCES[device] = ocr
        ocr_result = ocr.predict(image_array)

    records = extract_texts_with_scores(ocr_result)
    lines: List[Tuple[str, float]] = []
    for item in records:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        score = float(item.get("score", 0.0))
        lines.append((text, _clip_conf(score)))

    return lines


def _extract_company(lines: Sequence[Tuple[str, float]]) -> Tuple[Optional[str], Optional[float]]:
    best_name: Optional[str] = None
    best_score = -1.0

    for text, score in lines:
        normalized = _normalize_text(text)
        for company, aliases in _COMPANY_ALIASES.items():
            for alias in aliases:
                alias_norm = _normalize_text(alias)
                if alias_norm and alias_norm in normalized:
                    candidate_score = _clip_conf(score * 0.9 + 0.1)
                    if candidate_score > best_score:
                        best_name = company
                        best_score = candidate_score

    if best_name is None:
        return None, None
    return best_name, round(best_score, 3)


def _extract_card_number(lines: Sequence[Tuple[str, float]]) -> Tuple[Optional[str], Optional[float]]:
    best_number: Optional[str] = None
    best_score = -1.0

    for text, score in lines:
        for match in _CARD_NUMBER_PATTERN.findall(text):
            digits = re.sub(r"\D", "", match)
            if not (14 <= len(digits) <= 19):
                continue
            formatted = _format_card_number(digits)
            candidate_score = _clip_conf(score * 0.9 + 0.1)
            if candidate_score > best_score:
                best_number = formatted
                best_score = candidate_score

    if best_number is None:
        best_number, best_score = _extract_card_number_by_group(lines)

    if best_number is None:
        return None, None
    return best_number, round(best_score, 3)


def _extract_card_number_by_group(
    lines: Sequence[Tuple[str, float]]
) -> Tuple[Optional[str], float]:
    digit_chunks: List[Tuple[str, float]] = []
    for text, score in lines:
        chunk = re.sub(r"\D", "", text)
        if 3 <= len(chunk) <= 6:
            digit_chunks.append((chunk, score))

    best_number: Optional[str] = None
    best_score = -1.0
    n = len(digit_chunks)
    for start in range(n):
        merged = ""
        scores: List[float] = []
        for end in range(start, min(n, start + 6)):
            merged += digit_chunks[end][0]
            scores.append(digit_chunks[end][1])
            if len(merged) > 19:
                break
            if 14 <= len(merged) <= 19:
                candidate_score = _clip_conf((sum(scores) / len(scores)) * 0.85)
                if candidate_score > best_score:
                    best_number = _format_card_number(merged)
                    best_score = candidate_score

    return best_number, best_score


def _extract_expiration_date(lines: Sequence[Tuple[str, float]]) -> Tuple[Optional[str], Optional[float]]:
    best_value: Optional[str] = None
    best_score = -1.0

    for text, score in lines:
        hint = _has_hint(text, _EXPIRY_HINTS)

        for month_raw, year_raw in _EXP_PATTERN.findall(text):
            value = _to_mm_yy(month_raw, year_raw)
            if value is None:
                continue
            candidate_score = _clip_conf(score + (0.08 if hint else 0.0))
            if candidate_score > best_score:
                best_value = value
                best_score = candidate_score

        if not hint:
            continue

        for month_raw, year_raw in _EXP_COMPACT_PATTERN.findall(text):
            value = _to_mm_yy(month_raw, year_raw)
            if value is None:
                continue
            candidate_score = _clip_conf(score + 0.05)
            if candidate_score > best_score:
                best_value = value
                best_score = candidate_score

    if best_value is None:
        return None, None
    return best_value, round(best_score, 3)


def _extract_cvc(
    lines: Sequence[Tuple[str, float]],
    card_number: Optional[str],
    expiration_date: Optional[str],
) -> Tuple[Optional[str], Optional[float]]:
    best_value: Optional[str] = None
    best_score = -1.0

    card_digits = re.sub(r"\D", "", card_number or "")
    exp_digits = re.sub(r"\D", "", expiration_date or "")

    for text, score in lines:
        normalized = _normalize_text(text)

        context_match = _CVC_CONTEXT_PATTERN.search(text)
        if context_match:
            candidate = context_match.group(1)
            candidate_score = _clip_conf(score * 0.85 + 0.15)
            if candidate_score > best_score:
                best_value = candidate
                best_score = candidate_score
            continue

        compact = re.sub(r"\D", "", text)
        if not re.fullmatch(r"\d{3,4}", compact):
            continue
        if compact == exp_digits:
            continue
        if card_digits and compact in card_digits and len(card_digits) >= 14:
            continue

        has_hint = _has_hint(normalized, _CVC_HINTS)
        candidate_score = _clip_conf(score * (0.8 if has_hint else 0.55))
        if candidate_score > best_score:
            best_value = compact
            best_score = candidate_score

    if best_value is None:
        return None, None
    return best_value, round(best_score, 3)


def _normalize_device(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in ("gpu", "cuda", "cuda:0"):
        return "gpu:0"
    if normalized.startswith("gpu"):
        return normalized
    return "cpu"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def _has_hint(text: str, hints: Sequence[str]) -> bool:
    normalized = _normalize_text(text)
    for hint in hints:
        if _normalize_text(hint) in normalized:
            return True
    return False


def _to_mm_yy(month_raw: str, year_raw: str) -> Optional[str]:
    try:
        month = int(month_raw)
    except ValueError:
        return None
    if month < 1 or month > 12:
        return None

    year_digits = re.sub(r"\D", "", year_raw or "")
    if len(year_digits) == 4:
        year_digits = year_digits[-2:]
    if len(year_digits) != 2:
        return None

    return f"{month:02d}/{year_digits}"


def _format_card_number(digits: str) -> str:
    if len(digits) == 16:
        parts = [digits[0:4], digits[4:8], digits[8:12], digits[12:16]]
    elif len(digits) == 15:
        parts = [digits[0:4], digits[4:10], digits[10:15]]
    else:
        parts = []
        cursor = 0
        while len(digits) - cursor > 4:
            parts.append(digits[cursor:cursor + 4])
            cursor += 4
        parts.append(digits[cursor:])
    return "-".join(part for part in parts if part)


def _clip_conf(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
