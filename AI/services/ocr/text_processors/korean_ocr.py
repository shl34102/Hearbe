# PaddleOCR 기반 한글 OCR 실행
import os

from paddleocr import PaddleOCR
from PIL import Image
from typing import List, Dict, Any, Optional

try:
    from .utils import get_image_size
except ImportError:
    from utils import get_image_size

# decompression bomb 방지 (약 14000x14000px 상한)
Image.MAX_IMAGE_PIXELS = 200_000_000

DEFAULT_MODEL_NAME = "korean_PP-OCRv5_mobile_rec"
MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024  # 이미지 파일 최대 50MB
DEFAULT_DEVICE = "gpu:0"

# 싱글톤 PaddleOCR 인스턴스 (warmup 시 미리 생성, GPU 단일 스레드에서 재사용)
_default_ocr_instance: PaddleOCR = None


def create_ocr_instance(
    model_name: str = DEFAULT_MODEL_NAME,
    device: str = DEFAULT_DEVICE,
    use_textline_orientation: bool = True
) -> PaddleOCR:
    return PaddleOCR(
        text_recognition_model_name=model_name,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=use_textline_orientation,
        device=device,
    )


def get_ocr_instance(device: str = DEFAULT_DEVICE) -> PaddleOCR:
    """싱글톤 PaddleOCR 인스턴스 반환. 없으면 생성."""
    global _default_ocr_instance
    if _default_ocr_instance is None:
        _default_ocr_instance = create_ocr_instance(device=device)
    return _default_ocr_instance


def run_ocr(
    image_path: str,
    ocr_instance: Optional[PaddleOCR] = None
) -> List[Any]:
    if ocr_instance is None:
        ocr_instance = get_ocr_instance()
    return ocr_instance.predict(image_path)


def extract_texts(ocr_result: List[Any]) -> List[str]:
    texts = []
    for res in ocr_result:
        if hasattr(res, 'get'):
            texts.extend(res.get('rec_texts', []))
        elif hasattr(res, 'rec_texts'):
            texts.extend(res.rec_texts)
    return texts


def extract_texts_with_scores(ocr_result: List[Any]) -> List[Dict[str, Any]]:
    results = []
    for res in ocr_result:
        if hasattr(res, 'get'):
            texts = res.get('rec_texts', [])
            scores = res.get('rec_scores', [])
            boxes = res.get('dt_polys', [])
        elif hasattr(res, 'rec_texts'):
            texts = res.rec_texts
            scores = res.rec_scores if hasattr(res, 'rec_scores') else [1.0] * len(texts)
            boxes = res.dt_polys if hasattr(res, 'dt_polys') else []
        else:
            continue

        # boxes가 없으면 빈 리스트로 채움
        if len(boxes) < len(texts):
            boxes = boxes + [[]] * (len(texts) - len(boxes))

        for text, score, box in zip(texts, scores, boxes):
            # NumPy 배열을 Python list로 변환
            if hasattr(box, 'tolist'):
                box = box.tolist()
            elif box and hasattr(box[0], 'tolist'):
                box = [pt.tolist() if hasattr(pt, 'tolist') else pt for pt in box]

            results.append({"text": text, "score": float(score), "box": box})
    return results


DEFAULT_MAX_HEIGHT = 2500


def process_image(
    image_path: str,
    max_height: int = DEFAULT_MAX_HEIGHT,
    save_chunks: bool = False,
    save_vis: bool = True,
    save_ocr_json: bool = True,
    output_dir: str = "output",
    ocr_instance: Optional[PaddleOCR] = None
) -> Dict[str, Any]:
    import json
    from pathlib import Path

    file_size = os.path.getsize(image_path)
    if file_size > MAX_IMAGE_FILE_SIZE:
        raise ValueError(
            f"이미지 파일이 너무 큽니다: {file_size / 1024 / 1024:.1f}MB (최대 {MAX_IMAGE_FILE_SIZE // 1024 // 1024}MB)"
        )

    width, height = get_image_size(image_path)
    
    if ocr_instance is None:
        ocr_instance = get_ocr_instance()

    if height > max_height:
        
        try:
            from . import long_image_processor
        except ImportError:
            import long_image_processor
        
        result = long_image_processor.process_long_image(
            image_path,
            max_height=max_height,
            save_chunks=save_chunks,
            ocr_instance=ocr_instance
        )
        result["processing_mode"] = "split"
    else:

        # RGBA(PNG 투명도) 처리를 위해 이미지를 RGB로 변환 후 numpy 배열로 전달
        import numpy as np
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img_array = np.array(img)
        img_array = img_array[:, :, ::-1]  # RGB to BGR
        ocr_raw_result = ocr_instance.predict(img_array)

        if save_vis:
            os.makedirs(output_dir, exist_ok=True)
            for res in ocr_raw_result:
                res.save_to_img(output_dir)

        texts_with_scores = extract_texts_with_scores(ocr_raw_result)


        result = {
            "rec_texts": [item["text"] for item in texts_with_scores],
            "rec_scores": [item["score"] for item in texts_with_scores],
            "boxes": [item["box"] for item in texts_with_scores],
            "total_count": len(texts_with_scores),
            "processing_mode": "direct",
            "image_size": {"width": int(width), "height": int(height)}
        }
    
    if save_ocr_json:
        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(image_path).stem
        output_path = os.path.join(output_dir, f"{base_name}_ocr_result.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def process_images_parallel(
    image_paths: List[str],
    max_workers: int = 4,
    max_height: int = DEFAULT_MAX_HEIGHT,
    save_results: bool = False,
    save_vis: bool = True,
    save_ocr_json: bool = True,
    output_dir: str = "output",
    device: str = DEFAULT_DEVICE
) -> List[Dict[str, Any]]:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    import threading
    import os

    os.makedirs(output_dir, exist_ok=True)
    thread_local = threading.local()

    def process_single(image_path: str) -> Dict[str, Any]:
        try:
            if not hasattr(thread_local, "ocr_instance"):
                thread_local.ocr_instance = get_ocr_instance(device=device)
            result = process_image(
                image_path,
                max_height=max_height,
                save_chunks=save_results,
                save_vis=save_vis,
                save_ocr_json=save_ocr_json,
                output_dir=output_dir,
                ocr_instance=thread_local.ocr_instance
            )
            result["source"] = Path(image_path).name
            return result
        except Exception as e:
            return {
                "rec_texts": [],
                "rec_scores": [],
                "boxes": [],
                "total_count": 0,
                "processing_mode": "error",
                "source": Path(image_path).name,
                "error": str(e)
            }

    results = []
    if isinstance(device, str) and device.startswith("gpu"):
        max_workers = 1  # GPU에서는 메모리 경합 방지를 위해 순차 처리
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(process_single, path): path 
            for path in image_paths
        }
        
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "rec_texts": [],
                    "rec_scores": [],
                    "boxes": [],
                    "total_count": 0,
                    "processing_mode": "error",
                    "source": Path(path).name,
                    "error": str(e)
                })
    
    path_order = {Path(p).name: i for i, p in enumerate(image_paths)}
    results.sort(key=lambda x: path_order.get(x["source"], 999))
    
    total_texts = sum(r["total_count"] for r in results)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="한국어 OCR")
    parser.add_argument("--input", default="../tests/fixtures/coupang_ohyes.jpg")
    parser.add_argument("--output", default="output")
    parser.add_argument("--max-height", type=int, default=DEFAULT_MAX_HEIGHT)
    parser.add_argument("--save-chunks", action="store_true")
    args = parser.parse_args()
    
    result = process_image(
        args.input,
        max_height=args.max_height,
        save_chunks=args.save_chunks,
        output_dir=args.output
    )
