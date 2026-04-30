"""
숫자 → DOM 키 매핑 모듈

추출된 숫자 리스트를 DOM 키와 매핑하고 TTS 텍스트를 생성합니다.

사용법:
    python digit_to_dom_mapper.py <digits_json> [output.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Union


def create_digit_to_key_mapping(
    digits: List[str], 
    dom_keys: List[str] = None
) -> Dict[str, str]:
    """
    추출된 숫자 리스트를 DOM 키와 매핑합니다.
    
    DOM 키 순서 (팀장 제공):
    0 1 2
    3 4 5
    6 7 8
      9
    
    Args:
        digits: 순서대로 정렬된 숫자 리스트 (길이 10)
        dom_keys: 팀장이 제공하는 DOM 키 리스트 (예: ["key-0", "key-1", ...])
                  None이면 기본값 ["0", "1", ..., "9"] 사용
    
    Returns:
        {숫자: DOM키} 딕셔너리
    """
    if dom_keys is None:
        dom_keys = [str(i) for i in range(10)]
    
    mapping = {}
    for idx, digit in enumerate(digits):
        if idx < len(dom_keys):
            mapping[digit] = dom_keys[idx]
    return mapping


def format_mapping_for_tts(mapping: Dict[str, str]) -> str:
    """
    매핑 결과를 TTS용 텍스트로 변환합니다.
    
    Args:
        mapping: {숫자: DOM키} 딕셔너리
    
    Returns:
        TTS용 문자열 (예: "0은 key 3. 1은 key 0. ...")
    """
    def _safe_int(s):
        try:
            return int(s)
        except (ValueError, TypeError):
            return float('inf')

    lines = []
    for digit in sorted(mapping.keys(), key=_safe_int):
        lines.append(f"{digit}은 key {mapping[digit]}")
    return ". ".join(lines)


def save_mapping_result(
    digits_json_path: Union[str, Path],
    output_path: Union[str, Path] = None,
    dom_keys: List[str] = None
) -> Dict:
    """
    숫자 추출 JSON을 읽어서 매핑 결과를 JSON 파일로 저장합니다.
    
    Args:
        digits_json_path: 1단계 숫자 추출 결과 JSON 파일 경로
        output_path: 출력 파일 경로 (None이면 자동 생성)
        dom_keys: 팀장이 제공하는 DOM 키 리스트
    
    Returns:
        매핑 결과 딕셔너리
    """
    digits_json_path = Path(digits_json_path)
    
    # 1단계 결과 로드
    with open(digits_json_path, 'r', encoding='utf-8') as f:
        digits_data = json.load(f)
    
    digits = digits_data.get("extracted_digits", [])
    
    # 매핑 생성
    if dom_keys is None:
        dom_keys = [str(i) for i in range(10)]
    
    mapping = create_digit_to_key_mapping(digits, dom_keys)
    
    # 결과 딕셔너리
    result = {
        "source_file": str(digits_json_path),
        "step": "2_dom_mapping",
        "digits": digits,
        "dom_keys": dom_keys,
        "digit_to_key_mapping": mapping
    }
    
    # 출력 경로 설정
    if output_path is None:
        output_path = digits_json_path.parent / f"{digits_json_path.stem.replace('_digits', '')}_mapped.json"
    
    # JSON 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


# CLI 실행
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].endswith(".json") else None

    dom_keys_path = None
    if len(sys.argv) > 3:
        dom_keys_path = sys.argv[3]
    elif len(sys.argv) > 2 and sys.argv[2].endswith("dom_keys.json"):
        dom_keys_path = sys.argv[2]
        output_path = None

    dom_keys = None
    if dom_keys_path:
        with open(dom_keys_path, 'r', encoding='utf-8') as f:
            dom_keys = json.load(f)

    save_mapping_result(json_path, output_path, dom_keys)




