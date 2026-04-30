"""
Payment OCR pipeline (image -> OCR -> digit extraction -> DOM mapping)

Usage:
    python payment_ocr_pipeline.py <image_path> [output_dir] [dom_keys.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

try:
    from .payment_ocr import run_ocr
    from .digit_extractor import save_extracted_digits
    from .digit_to_dom_mapper import save_mapping_result
except ImportError:
    from payment_ocr import run_ocr
    from digit_extractor import save_extracted_digits
    from digit_to_dom_mapper import save_mapping_result


def run_pipeline(
    image_path: str,
    output_dir: str = "output",
    dom_keys_path: Optional[str] = None,
) -> str:
    """
    Run full payment OCR pipeline.

    Args:
        image_path: input image path
        output_dir: directory to write outputs
        dom_keys_path: optional path to dom_keys.json

    Returns:
        Path to final mapped JSON file.
    """
    output_dir = str(output_dir)

    # Step 0: OCR (image -> *_res.json)
    ocr_json_path = run_ocr(image_path, output_dir)

    # Step 1: digit extraction (-> *_digits.json)
    save_extracted_digits(ocr_json_path)
    ocr_json_path = Path(ocr_json_path)
    digits_json_path = ocr_json_path.parent / f"{ocr_json_path.stem}_digits.json"

    # Step 2: DOM mapping (-> *_mapped.json)
    dom_keys: Optional[List[str]] = None
    if dom_keys_path:
        with open(dom_keys_path, "r", encoding="utf-8") as f:
            dom_keys = json.load(f)

    mapped_result = save_mapping_result(
        str(digits_json_path),
        output_path=None,
        dom_keys=dom_keys,
    )
    mapped_json_path = digits_json_path.parent / f"{digits_json_path.stem.replace('_digits', '')}_mapped.json"

    # Keep only the final mapped JSON; remove intermediate OCR/digits JSON
    for path in (ocr_json_path, digits_json_path):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    return str(mapped_json_path)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(1)

    image_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    dom_keys_path = sys.argv[3] if len(sys.argv) > 3 else None

    run_pipeline(image_path, output_dir, dom_keys_path)


if __name__ == "__main__":
    main()
