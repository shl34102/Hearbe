# OCR 전체 처리 파이프라인
import argparse
import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

try:
    from .korean_ocr import process_image, process_images_parallel
    from .ocr_text_preprocessor import filter_texts, preprocess_ocr_texts, extract_rec_texts_from_data
    from .ocr_text_merger import merge_ocr_results
    from .product_type_detector import (
        ProductType,
        detect_product_type,
        get_type_description,
        override_product_type,
    )
    from .ocr_llm_summarizer import summarize_texts
    from .image_fetcher import (
        filter_product_images,
        download_images,
        detect_site,
        get_selector,
        list_supported_sites,
    )
    from .table_reconstructor import reconstruct_size_table
    from .utils import save_json
except ImportError:
    from korean_ocr import process_image, process_images_parallel
    from ocr_text_preprocessor import filter_texts, preprocess_ocr_texts, extract_rec_texts_from_data
    from ocr_text_merger import merge_ocr_results
    from product_type_detector import (
        ProductType,
        detect_product_type,
        get_type_description,
        override_product_type,
    )
    from ocr_llm_summarizer import summarize_texts
    from image_fetcher import (
        filter_product_images,
        download_images,
        detect_site,
        get_selector,
        list_supported_sites,
    )
    from table_reconstructor import reconstruct_size_table
    from utils import save_json


def _summary_only(summary: Dict) -> Dict:
    return {"summary": summary.get("summary", [])}


_IMPORTANT_TOKENS = (
    "특가", "할인", "세일", "반값", "쿠폰", "무료배송",
    "원산지", "제조", "브랜드", "유통기한", "보관",
    "용량", "중량", "구성", "증정", "1+1", "2+1",
    "원", "%", "kg", "g", "ml", "l", "개", "입", "팩", "박스",
    # 의류 사이즈 관련
    "SIZE", "사이즈", "허리", "총장", "엉덩이", "앞밑위", "뒷밑위",
    "가슴", "어깨", "소매", "밑단", "허벅지", "암홀", "기장",
    "M", "L", "XL", "2XL", "FREE", "프리"
)


def _is_important_text(text: str) -> bool:
    for token in _IMPORTANT_TOKENS:
        if token in text:
            return True
    # 숫자 + 단위/통화 패턴
    return bool(re.search(r"\d+\s*(원|%|kg|g|ml|l|개|입|팩|박스)", text.lower()))


def _select_texts_by_importance(
    filtered: List[Tuple[str, float]],
    max_items: int = 100
) -> List[str]:
    """중요도 기반 텍스트 선별: 중요 키워드 포함 텍스트 우선 + 높은 스코어 순"""
    if len(filtered) <= max_items:
        return [text for text, score in filtered]

    important = []
    normal = []

    for text, score in filtered:
        if _is_important_text(text):
            important.append((text, score))
        else:
            normal.append((text, score))

    # 각 그룹 내에서 스코어 높은 순 정렬
    important.sort(key=lambda x: x[1], reverse=True)
    normal.sort(key=lambda x: x[1], reverse=True)

    # 중요 텍스트 우선 선택
    selected = important + normal
    return [text for text, score in selected[:max_items]]


def process_product_image(
    image_path: str,
    output_dir: str = "output",
    save_result: bool = False,
    verbose: bool = True,
    use_cache: bool = True
) -> Dict:
    start_time = time.time()

    ocr_result = process_image(image_path, output_dir=output_dir, save_vis=False, save_ocr_json=False)
    ocr_count = ocr_result.get("total_count", len(ocr_result.get("rec_texts", [])))

    raw_texts = ocr_result.get("rec_texts", [])
    raw_scores = ocr_result.get("rec_scores", [1.0] * len(raw_texts))

    filtered = filter_texts(
        raw_texts,
        raw_scores,
        min_score=0.7,
        min_length=2,
        important_text_predicate=_is_important_text,
    )
    filtered_texts = _select_texts_by_importance(filtered, max_items=100)

    product_type = detect_product_type(filtered_texts)
    product_type = override_product_type(filtered_texts, product_type)

    size_table_text = None
    if product_type in [ProductType.의류, ProductType.신발, ProductType.패션잡화]:
        original_texts = ocr_result.get("rec_texts", [])
        original_boxes = ocr_result.get("boxes", [])
        original_scores = ocr_result.get("rec_scores", [1.0] * len(original_texts))
        if original_boxes:
            size_table_text = reconstruct_size_table(original_texts, original_boxes, original_scores)

    # [DEBUG] 필터링된 텍스트 & 사이즈 테이블을 output에 JSON 저장
    if save_result:
        base_name = Path(image_path).stem
        debug_data = {
            "filtered_texts": filtered_texts,
            "size_table": size_table_text,
            "product_type": product_type.value,
        }
        save_json(debug_data, os.path.join(output_dir, f"{base_name}_debug.json"))

    summary = summarize_texts(
        filtered_texts,
        product_type,
        verbose=False,
        use_cache=use_cache,
        size_table=size_table_text
    )

    elapsed_time = time.time() - start_time
    summary["source_image"] = str(image_path)
    summary["ocr_count"] = ocr_count
    summary["filtered_count"] = len(filtered_texts)
    summary["processing_time"] = round(elapsed_time, 2)

    return summary


def process_multiple_images(
    image_paths: List[str],
    output_dir: str = "output",
    max_workers: int = 4,
    save_result: bool = False,
    verbose: bool = True,
    use_cache: bool = True
) -> Dict:
    start_time = time.time()

    ocr_results = process_images_parallel(
        image_paths,
        max_workers=max_workers,
        output_dir=output_dir,
        save_vis=False,
        save_ocr_json=False
    )
    total_ocr = sum(r.get("total_count", 0) for r in ocr_results)

    merged = merge_ocr_results(ocr_results)

    raw_texts = merged.get("rec_texts", [])
    raw_scores = merged.get("rec_scores", [1.0] * len(raw_texts))

    filtered = filter_texts(
        raw_texts,
        raw_scores,
        min_score=0.7,
        min_length=2,
        important_text_predicate=_is_important_text,
    )
    filtered_texts = _select_texts_by_importance(filtered, max_items=100)

    product_type = detect_product_type(filtered_texts)
    product_type = override_product_type(filtered_texts, product_type)

    size_table_text = None
    if product_type in [ProductType.의류, ProductType.신발, ProductType.패션잡화]:
        size_header_patterns = [
            "허리", "엉덩이", "총장", "밑위", "허벅지", "바지길이", "힙둘레", "밑단",
            "어깨", "가슴", "소매", "기장",
            "룸", "발볼", "무게", "굽높이", "발폭", "밑창길이",
            "참고사이즈", "남성사이즈", "여성사이즈", "길이단위",
            "사이즈", "신발",
        ]
        size_image_result = None
        best_header_count = 0

        for ocr_result in ocr_results:
            result_texts = ocr_result.get("rec_texts", [])
            combined = " ".join(str(t) for t in result_texts)
            header_count = sum(1 for pattern in size_header_patterns if pattern in combined)
            if header_count >= 2 and header_count > best_header_count:
                best_header_count = header_count
                size_image_result = ocr_result

        if size_image_result:
            size_texts = size_image_result.get("rec_texts", [])
            size_scores = size_image_result.get("rec_scores", [1.0] * len(size_texts))
            size_boxes = size_image_result.get("boxes", [])
            if size_boxes:
                size_table_text = reconstruct_size_table(size_texts, size_boxes, size_scores)

    # [DEBUG] 필터링된 텍스트 & 사이즈 테이블을 output에 JSON 저장
    if save_result and image_paths:
        first_name = Path(image_paths[0]).stem
        debug_data = {
            "filtered_texts": filtered_texts,
            "size_table": size_table_text,
            "product_type": product_type.value,
        }
        save_json(debug_data, os.path.join(output_dir, f"{first_name}_debug.json"))

    summary = summarize_texts(
        filtered_texts,
        product_type,
        verbose=False,
        use_cache=use_cache,
        size_table=size_table_text
    )

    elapsed_time = time.time() - start_time
    summary["source_images"] = [str(p) for p in image_paths]
    summary["image_count"] = len(image_paths)
    summary["ocr_count"] = total_ocr
    summary["merged_count"] = merged["count"]
    summary["filtered_count"] = len(filtered_texts)
    summary["processing_time"] = round(elapsed_time, 2)

    if save_result and image_paths:
        first_name = Path(image_paths[0]).stem
        output_path = os.path.join(output_dir, f"{first_name}_merged_summary.json")
        save_json(_summary_only(summary), output_path)

    return summary


def process_product_from_urls(
    image_urls: List[str],
    site: str = "auto",
    output_dir: str = "output",
    max_workers: int = 4,
    save_result: bool = False,
    verbose: bool = True,
    use_cache: bool = True
) -> Dict:
    start_time = time.time()

    filtered_urls = filter_product_images(image_urls, site=site)

    if not filtered_urls:
        return {
            "summary": ["상품 상세 이미지를 찾을 수 없습니다."],
            "product_name": "알 수 없음",
            "product_type": "기타",
            "source_urls": image_urls,
            "error": "no_images_after_filter"
        }

    download_dir = os.path.join(output_dir, "downloaded")
    local_paths = download_images(
        filtered_urls,
        save_dir=download_dir,
        max_workers=max_workers
    )

    if not local_paths:
        return {
            "summary": ["이미지 다운로드에 실패했습니다."],
            "product_name": "알 수 없음",
            "product_type": "기타",
            "source_urls": filtered_urls,
            "error": "download_failed"
        }

    result = process_multiple_images(
        image_paths=local_paths,
        output_dir=output_dir,
        max_workers=max_workers,
        save_result=save_result,
        verbose=False,
        use_cache=use_cache
    )

    # 다운로드된 중간 이미지 정리
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir, ignore_errors=True)

    elapsed_time = time.time() - start_time
    result["source_urls"] = filtered_urls
    result["site"] = site if site != "auto" else detect_site(filtered_urls[0]) if filtered_urls else "unknown"
    result["total_processing_time"] = round(elapsed_time, 2)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OCR 통합 파이프라인"
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", "-i")
    input_group.add_argument("--inputs", "-I", nargs="+")
    input_group.add_argument("--urls", "-U", nargs="+")

    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--workers", "-w", type=int, default=4)
    parser.add_argument("--site", "-s", default="auto", choices=["auto", "coupang", "naver"])
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")

    args = parser.parse_args()

    try:
        if args.input:
            result = process_product_image(
                image_path=args.input,
                output_dir=args.output_dir,
                save_result=not args.no_save,
                verbose=False,
                use_cache=False
            )
        elif args.inputs:
            result = process_multiple_images(
                image_paths=args.inputs,
                output_dir=args.output_dir,
                max_workers=args.workers,
                save_result=not args.no_save,
                verbose=False,
                use_cache=False
            )
        else:
            result = process_product_from_urls(
                image_urls=args.urls,
                site=args.site,
                output_dir=args.output_dir,
                max_workers=args.workers,
                save_result=not args.no_save,
                verbose=False,
                use_cache=False
            )

        if args.output:
            save_json(_summary_only(result), args.output)

        return 0

    except Exception:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

