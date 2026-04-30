# -*- coding: utf-8 -*-
"""
Keypad OCR helper.

Takes a keypad image, runs OCR, and returns digit-to-key mapping.
"""

import os
import tempfile
import time
import threading
from typing import Dict, List, Optional

from services.ocr.text_processors import korean_ocr
from services.ocr.payment.digit_extractor import extract_digits_from_ocr_result
from services.ocr.payment.digit_to_dom_mapper import create_digit_to_key_mapping

_OCR_LOCK = threading.Lock()
_OCR_INSTANCE = None
_OCR_INSTANCE_READY = False


def _get_ocr_instance(device: str):
    global _OCR_INSTANCE
    global _OCR_INSTANCE_READY
    if _OCR_INSTANCE is None:
        start = time.time()
        _OCR_INSTANCE = korean_ocr.create_ocr_instance(device=device)
        _OCR_INSTANCE_READY = True
        duration = time.time() - start
        try:
            import logging
            logging.getLogger(__name__).info(
                "Keypad OCR instance initialized: device=%s duration=%.2fs",
                device,
                duration,
            )
        except Exception:
            pass
    return _OCR_INSTANCE


def map_keypad_image(
    image_bytes: bytes,
    dom_keys: Optional[List[str]] = None,
    device: str = "cpu",
) -> Dict[str, object]:
    """
    Run OCR on keypad image and map digits to DOM keys.

    Returns:
        {
          "digits": [...],
          "dom_keys": [...],
          "digit_to_key_mapping": {...}
        }
    """
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")

    if not dom_keys:
        dom_keys = [str(i) for i in range(10)]

    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "keypad.png")
        with open(image_path, "wb") as f:
            f.write(image_bytes)

        with _OCR_LOCK:
            start = time.time()
            ocr = _get_ocr_instance(device)
            # 파일 경로를 직접 전달 (process_image의 numpy 변환은 키패드에 불필요)
            ocr_raw = korean_ocr.run_ocr(image_path, ocr_instance=ocr)
            duration = time.time() - start
            try:
                import logging
                logging.getLogger(__name__).info(
                    "Keypad OCR process completed: device=%s duration=%.2fs",
                    device,
                    duration,
                )
            except Exception:
                pass

    texts_with_scores = korean_ocr.extract_texts_with_scores(ocr_raw)
    ocr_result = {
        "rec_texts": [item["text"] for item in texts_with_scores],
        "rec_scores": [item["score"] for item in texts_with_scores],
    }
    digits = extract_digits_from_ocr_result(ocr_result)
    mapping = create_digit_to_key_mapping(digits, dom_keys)
    return {
        "digits": digits,
        "dom_keys": dom_keys,
        "digit_to_key_mapping": mapping,
    }


def is_ocr_instance_ready() -> bool:
    return _OCR_INSTANCE_READY
