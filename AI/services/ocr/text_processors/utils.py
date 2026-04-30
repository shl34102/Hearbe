# OCR 공통 유틸
import json
import logging
import os
import tempfile
from typing import Any, Dict, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ==================== 이미지 유틸 ====================


def save_json(data: Dict[str, Any], output_path: str, indent: int = 2) -> None:
    """JSON 파일 저장 (원자적 쓰기: 임시파일에 쓴 뒤 교체하여 동시성 안전)"""
    dir_name = os.path.dirname(output_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_json(input_path: str) -> Dict[str, Any]:
    """JSON 파일 로드 (공통 함수)"""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_image_size(image_path: str) -> Tuple[int, int]:
    """이미지 크기 반환 (width, height)"""
    with Image.open(image_path) as img:
        return img.size


def prepare_image_for_ocr(img: Image.Image) -> np.ndarray:
    """PIL Image를 OCR용 BGR numpy 배열로 변환 (RGBA/기타 모드 → RGB → BGR)"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    arr = np.array(img)
    return arr[:, :, ::-1]  # RGB → BGR
