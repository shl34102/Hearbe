"""
OCR 결과에서 숫자만 추출하는 모듈

결제 키패드 OCR 결과에서 0-9 숫자만 필터링하고 정렬합니다.

사용법:
    python digit_extractor.py <ocr_result.json> [output.json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Union


def extract_digits_from_ocr_result(ocr_result: Dict) -> List[str]:
    """
    OCR 결과 JSON에서 숫자만 추출합니다. (원본 순서 유지)
    
    Args:
        ocr_result: PaddleOCR 결과 딕셔너리 (rec_texts 포함)
    
    Returns:
        숫자만 포함된 리스트 (원본 순서 유지)
    """
    rec_texts = ocr_result.get("rec_texts", [])
    
    # 숫자만 필터링 (0-9 한 글자), 순서는 원본 그대로 유지
    digits = [text.strip() for text in rec_texts if re.match(r'^[0-9]$', text.strip())]
    
    return digits


def extract_digits_from_json_file(json_path: Union[str, Path]) -> List[str]:
    """
    OCR 결과 JSON 파일에서 숫자를 추출합니다.
    
    Args:
        json_path: OCR 결과 JSON 파일 경로
    
    Returns:
        숫자 리스트 (정렬된 순서)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        ocr_result = json.load(f)
    
    return extract_digits_from_ocr_result(ocr_result)


def save_extracted_digits(
    ocr_json_path: Union[str, Path],
    output_path: Union[str, Path] = None
) -> Dict:
    """
    OCR 결과에서 숫자만 추출하여 JSON 파일로 저장합니다.
    
    Args:
        ocr_json_path: OCR 결과 JSON 파일 경로
        output_path: 출력 파일 경로 (None이면 자동 생성)
    
    Returns:
        추출 결과 딕셔너리
    """
    ocr_json_path = Path(ocr_json_path)
    
    # OCR 결과 로드
    with open(ocr_json_path, 'r', encoding='utf-8') as f:
        ocr_result = json.load(f)
    
    # 숫자 추출
    digits = extract_digits_from_ocr_result(ocr_result)
    
    # 결과 딕셔너리
    result = {
        "source_file": str(ocr_json_path),
        "step": "1_digit_extraction",
        "extracted_digits": digits,
        "total_count": len(digits)
    }
    
    # 출력 경로 설정
    if output_path is None:
        output_path = ocr_json_path.parent / f"{ocr_json_path.stem}_digits.json"
    
    # JSON 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


# CLI 실행
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    save_extracted_digits(json_path, output_path)


