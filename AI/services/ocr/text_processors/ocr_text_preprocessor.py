# OCR 텍스트 정제·필터링
import re
from typing import Callable, Dict, List, Optional, Tuple


def normalize_text(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", text).lower()


def is_meaningful_text(text: str) -> bool:
    has_korean = bool(re.search(r'[가-힣]', text))
    has_english_word = bool(re.search(r'[a-zA-Z]{2,}', text))
    alphanumeric_count = len(re.findall(r'[가-힣a-zA-Z0-9]', text))
    alphanumeric_ratio = alphanumeric_count / max(len(text), 1)
    return (has_korean or has_english_word) and alphanumeric_ratio > 0.5


def filter_texts(
    texts: List[str],
    scores: List[float],
    min_score: float = 0.7,
    min_length: int = 2,
    important_text_predicate: Optional[Callable[[str], bool]] = None,
) -> List[Tuple[str, float]]:
    filtered: List[Tuple[str, float]] = []

    for text, score in zip(texts, scores):
        if not isinstance(text, str):
            continue
        text = text.strip()
        if not text:
            continue

        # 중요 텍스트 여부 미리 판단 (점수/의미 필터 우회용)
        is_important = important_text_predicate and important_text_predicate(text)

        if score < min_score:
            if not is_important:
                continue
        if len(text) < min_length:
            if not is_important:  # 중요 텍스트면 min_length 우회 (M, L, XL 등)
                continue
        if not is_meaningful_text(text):
            if not is_important:  # 중요 텍스트면 is_meaningful_text 우회
                continue
        filtered.append((text, score))

    return filtered


def preprocess_ocr_texts(
    texts: List[str],
    scores: List[float],
    min_score: float = 0.7,
    min_length: int = 2,
    verbose: bool = True
) -> Tuple[List[str], Dict]:
    if len(texts) != len(scores):
        raise ValueError(f"texts와 scores의 길이가 같아야 합니다: {len(texts)} vs {len(scores)}")
    
    cleaned = []
    filtered_examples = {
        "by_score": [],
        "by_length": [],
        "by_pattern": []
    }
    
    stats = {
        "original_count": len(texts),
        "filtered_by_score": 0,
        "filtered_by_length": 0,
        "filtered_by_pattern": 0,
        "duplicates_removed": 0,
        "final_count": 0
    }
    
    for text, score in zip(texts, scores):
        text = text.strip()
        
        if score < min_score:
            stats["filtered_by_score"] += 1
            if len(filtered_examples["by_score"]) < 3:
                filtered_examples["by_score"].append(f'"{text}" (점수: {score:.2f})')
            continue
            
        if len(text) < min_length:
            stats["filtered_by_length"] += 1
            if len(filtered_examples["by_length"]) < 3:
                filtered_examples["by_length"].append(f'"{text}" (길이: {len(text)})')
            continue
            
        if not is_meaningful_text(text):
            stats["filtered_by_pattern"] += 1
            if len(filtered_examples["by_pattern"]) < 3:
                filtered_examples["by_pattern"].append(f'"{text}"')
            continue
            
        cleaned.append(text)
    
    original_cleaned_count = len(cleaned)
    cleaned = list(dict.fromkeys(cleaned))
    stats["duplicates_removed"] = original_cleaned_count - len(cleaned)
    stats["final_count"] = len(cleaned)
    
    return cleaned, stats


def load_and_preprocess_ocr_json(
    json_data: Dict,
    min_score: float = 0.7,
    min_length: int = 2,
    verbose: bool = True
) -> Tuple[List[str], Dict]:
    texts = json_data.get("rec_texts", [])
    scores = json_data.get("rec_scores", [])
    
    if not texts:
        raise ValueError("JSON 데이터에 'rec_texts'가 없습니다.")
    
    if not scores:
        scores = [1.0] * len(texts)
    
    return preprocess_ocr_texts(texts, scores, min_score, min_length, verbose)


def extract_rec_texts_from_data(data: Dict) -> List[str]:
    """OCR 결과 딕셔너리에서 유효한 텍스트만 추출"""
    rec_texts = data.get("rec_texts", [])
    cleaned = []
    for text in rec_texts:
        if not isinstance(text, str):
            continue
        text = text.strip()
        if not text:
            continue
        if not normalize_text(text):
            continue
        cleaned.append(text)
    return cleaned


if __name__ == "__main__":
    import json
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python ocr_text_preprocessor.py <ocr_json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    cleaned_texts, stats = load_and_preprocess_ocr_json(data, verbose=True)
    
    print("\n정제된 텍스트 목록:")
    for i, text in enumerate(cleaned_texts, 1):
        print(f"{i}. {text}")
