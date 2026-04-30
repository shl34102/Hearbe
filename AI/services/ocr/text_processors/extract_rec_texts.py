# OCR JSON에서 rec_texts만 추출 
import argparse
import json
import os
from pathlib import Path

try:
    from .ocr_text_preprocessor import extract_rec_texts_from_data
except ImportError:
    from ocr_text_preprocessor import extract_rec_texts_from_data

DEFAULT_INPUT = os.path.join("output", "초코파이_detail_res.json")
DEFAULT_OUTPUT = os.path.join("output", "초코파이_detail_res_texts.json")


def extract_rec_texts(input_path: str, output_path: str = None) -> list:
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    rec_texts = extract_rec_texts_from_data(data)
    
    if output_path is None:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}_texts.json")
    
    result = {
        "rec_texts": rec_texts,
        "count": len(rec_texts)
    }
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return rec_texts


def main():
    parser = argparse.ArgumentParser(description="OCR JSON에서 텍스트 추출")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    
    extract_rec_texts(args.input, args.output)


if __name__ == "__main__":
    main()
