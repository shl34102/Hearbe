# 긴 이미지 분할 및 OCR 처리
import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

# decompression bomb 방지 (약 14000x14000px 상한)
Image.MAX_IMAGE_PIXELS = 200_000_000

logger = logging.getLogger(__name__)

try:
    from . import korean_ocr
    from .utils import get_image_size, save_json
except ImportError:
    import korean_ocr
    from utils import get_image_size, save_json

DEFAULT_MAX_HEIGHT = 2500
DEFAULT_OVERLAP = 100
DEFAULT_RESIZE_MAX_HEIGHT = 12000
MIN_CHUNK_HEIGHT = 500
MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024  # 이미지 파일 최대 50MB
OUTPUT_DIR = "output"


def should_split_image(image_path: str, max_height: int = DEFAULT_MAX_HEIGHT) -> bool:
    width, height = get_image_size(image_path)
    return height > max_height


def split_image_to_chunks(
    image_path: str,
    max_height: int = DEFAULT_MAX_HEIGHT,
    overlap: int = DEFAULT_OVERLAP,
    resize_max_height: int = DEFAULT_RESIZE_MAX_HEIGHT,
    save_chunks: bool = False,
    output_dir: str = None
) -> List[Tuple[Image.Image, int]]:
    img = Image.open(image_path)
    width, height = img.size
    
    if resize_max_height and height > resize_max_height:
        scale = resize_max_height / height
        new_size = (max(1, int(width * scale)), resize_max_height)
        img = img.resize(new_size, Image.LANCZOS)
        width, height = img.size
    
    if save_chunks:
        base_name = Path(image_path).stem
        chunk_dir = output_dir or os.path.join(OUTPUT_DIR, "chunks", base_name)
        os.makedirs(chunk_dir, exist_ok=True)
    
    chunks = []
    y = 0
    chunk_index = 0
    
    while y < height:
        y_end = min(y + max_height, height)
        
        remaining = height - y_end
        if 0 < remaining < MIN_CHUNK_HEIGHT:
            y_end = height
        
        chunk = img.crop((0, y, width, y_end))
        chunks.append((chunk, y))
        
        if save_chunks:
            chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index + 1:02d}_y{y}-{y_end}.jpg")
            chunk.save(chunk_path, "JPEG", quality=95)
        
        chunk_index += 1
        y = y_end - overlap
        
        if y_end >= height:
            break
    
    return chunks


def process_chunk_ocr(chunk: Image.Image, ocr_instance) -> List[Dict]:
    """청크 이미지에 OCR 수행 (numpy 배열 직접 전달로 임시파일 생략)"""
    try:
        # RGBA(4채널) -> RGB(3채널) 변환 (PNG 투명도 처리)
        if chunk.mode != 'RGB':
            chunk = chunk.convert('RGB')

        # PIL Image -> numpy array (RGB -> BGR for OpenCV compatibility)
        img_array = np.array(chunk)
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img_array = img_array[:, :, ::-1]  # RGB to BGR
        return ocr_instance.predict(img_array)
    except Exception as e:
        logger.warning(f"Chunk OCR failed: {e}")
        return []


def adjust_coordinates(ocr_result: List[Dict], y_offset: int) -> List[Dict]:
    adjusted = []

    for res in ocr_result:
        if hasattr(res, 'get'):
            new_res = res.copy()
            if 'dt_polys' in new_res:
                polys = new_res['dt_polys']
                adjusted_polys = []
                for poly in polys:
                    adjusted_poly = [[p[0], p[1] + y_offset] for p in poly]
                    adjusted_polys.append(adjusted_poly)
                new_res['dt_polys'] = adjusted_polys
            adjusted.append(new_res)
        else:
            adjusted.append(res)

    return adjusted


def remove_duplicate_texts(all_results: List[Dict], overlap: int) -> Dict:
    seen_texts = set()
    unique_texts = []
    unique_scores = []
    unique_boxes = []

    for result in all_results:
        if isinstance(result, list):
            for res in result:
                # 딕셔너리와 객체 모두 처리
                if hasattr(res, 'get'):
                    texts = res.get('rec_texts', [])
                    scores = res.get('rec_scores', [])
                    polys = res.get('dt_polys', [])
                elif hasattr(res, 'rec_texts'):
                    texts = res.rec_texts if hasattr(res, 'rec_texts') else []
                    scores = res.rec_scores if hasattr(res, 'rec_scores') else []
                    polys = res.dt_polys if hasattr(res, 'dt_polys') else []
                else:
                    continue

                for idx, (text, score) in enumerate(zip(texts, scores)):
                    normalized = text.strip().lower()
                    if not normalized:
                        continue
                    key = normalized
                    box = polys[idx] if polys and idx < len(polys) else []

                    # NumPy 배열을 Python list로 변환 (좌표값도 float로 변환)
                    if hasattr(box, 'tolist'):
                        box = [[float(p[0]), float(p[1])] for p in box]
                    elif box and len(box) > 0:
                        if hasattr(box[0], 'tolist'):
                            box = [[float(p[0]), float(p[1])] for p in box]
                        elif isinstance(box[0], (list, tuple)) and len(box[0]) >= 2:
                            box = [[float(p[0]), float(p[1])] for p in box]

                    if polys and idx < len(polys):
                        poly = polys[idx]
                        if poly:
                            min_y = min(p[1] for p in poly)
                            bucket = int(min_y / max(overlap, 1))
                            key = f"{normalized}|{bucket}"
                    if key not in seen_texts:
                        seen_texts.add(key)
                        unique_texts.append(text)
                        unique_scores.append(float(score))  # float로 변환
                        unique_boxes.append(box)

    return {
        "rec_texts": unique_texts,
        "rec_scores": unique_scores,
        "boxes": unique_boxes,
        "total_count": len(unique_texts)
    }


def process_long_image(
    image_path: str,
    max_height: int = DEFAULT_MAX_HEIGHT,
    overlap: int = DEFAULT_OVERLAP,
    ocr_instance = None,
    save_chunks: bool = False
) -> Dict:
    file_size = os.path.getsize(image_path)
    if file_size > MAX_IMAGE_FILE_SIZE:
        raise ValueError(
            f"이미지 파일이 너무 큽니다: {file_size / 1024 / 1024:.1f}MB (최대 {MAX_IMAGE_FILE_SIZE // 1024 // 1024}MB)"
        )

    width, height = get_image_size(image_path)
    
    if not should_split_image(image_path, max_height):
        if ocr_instance:
            result = ocr_instance.predict(image_path)
            all_texts = []
            all_scores = []
            all_boxes = []
            for res in result:
                all_texts.extend(res.get('rec_texts', []))
                all_scores.extend(res.get('rec_scores', []))
                dt_polys = res.get('dt_polys', [])
                # NumPy 배열을 Python list로 변환 (좌표값도 float로 변환)
                for poly in dt_polys:
                    if poly is not None and len(poly) > 0:
                        all_boxes.append([[float(p[0]), float(p[1])] for p in poly])
                    else:
                        all_boxes.append([])
            return {
                "rec_texts": all_texts,
                "rec_scores": [float(s) for s in all_scores],
                "boxes": all_boxes,
                "total_count": len(all_texts),
                "split_count": 1,
                "image_size": {"width": int(width), "height": int(height)}
            }
        return {"error": "OCR 인스턴스가 필요합니다."}
    
    if ocr_instance is None:
        ocr_instance = korean_ocr.create_ocr_instance()
    
    chunks = split_image_to_chunks(image_path, max_height, overlap, save_chunks=save_chunks)
    
    if save_chunks:
        base_name = Path(image_path).stem
        debug_dir = os.path.join(OUTPUT_DIR, "chunks", base_name)
        os.makedirs(debug_dir, exist_ok=True)
    
    all_results = []
    for idx, (chunk, y_offset) in enumerate(chunks):
        
        result = process_chunk_ocr(chunk, ocr_instance)
        
        if save_chunks:
            chunk_texts = []
            for res in result:
                if hasattr(res, 'get'):
                    chunk_texts.extend(res.get('rec_texts', []))
                if hasattr(res, 'save_to_img'):
                    res.save_to_img(debug_dir)
            
            chunk_result_path = os.path.join(debug_dir, f"chunk_{idx + 1:02d}_result.json")
            with open(chunk_result_path, "w", encoding="utf-8") as f:
                json.dump({"chunk_index": idx + 1, "y_offset": y_offset, "texts": chunk_texts}, f, ensure_ascii=False, indent=2)
        
        adjusted = adjust_coordinates(result, y_offset)
        all_results.append(adjusted)
    
    merged = remove_duplicate_texts(all_results, overlap)
    merged["split_count"] = len(chunks)
    merged["image_size"] = {"width": int(width), "height": int(height)}
    merged["processing_mode"] = "split"

    return merged


def main():
    parser = argparse.ArgumentParser(description="긴 이미지 OCR 처리")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-height", type=int, default=DEFAULT_MAX_HEIGHT)
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    parser.add_argument("--save-chunks", action="store_true")
    args = parser.parse_args()
    
    ocr = korean_ocr.create_ocr_instance()
    
    result = process_long_image(
        args.input,
        max_height=args.max_height,
        overlap=args.overlap,
        ocr_instance=ocr,
        save_chunks=args.save_chunks
    )
    
    if args.output is None:
        base_name = Path(args.input).stem
        output_path = os.path.join(OUTPUT_DIR, f"{base_name}_long_ocr.json")
    else:
        output_path = args.output
    
    save_json(result, output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
