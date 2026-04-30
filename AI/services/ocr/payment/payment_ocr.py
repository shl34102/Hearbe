"""
결제 화면 OCR 인식 모듈

결제 비밀번호 입력 화면의 숫자 키패드를 OCR로 인식합니다.

사용법:
    python payment_ocr.py <이미지경로> [출력폴더]
"""
from paddleocr import PaddleOCR
import sys
import threading
from pathlib import Path

# PaddleOCR 인스턴스 (lazy loading: 실제 사용 시점에 초기화)
_ocr_instance = None
_ocr_lock = threading.Lock()


def _get_ocr():
    """
    PaddleOCR 인스턴스를 반환합니다. (최초 호출 시 1회만 초기화, 스레드 안전)

    한국어 인식에 최적화된 설정을 사용하여 OCR 엔진을 로드합니다.
    처음 실행 시 모델 파일을 자동으로 다운로드하므로 시간이 조금 걸릴 수 있습니다.
    """
    global _ocr_instance
    if _ocr_instance is None:
        with _ocr_lock:
            if _ocr_instance is None:
                _ocr_instance = PaddleOCR(
                    # 한국어 텍스트 인식 모델 사용 (korean_PP-OCRv5_mobile_rec)
                    text_recognition_model_name="korean_PP-OCRv5_mobile_rec",

                    # 문서 방향 분류(0도, 90도, 180도 등) 모델 사용 여부
                    # False로 설정하여 불필요한 연산을 줄이고 속도를 높입니다. (이미지가 정방향이라고 가정)
                    use_doc_orientation_classify=False,

                    # 문서가 구겨지거나 왜곡된 것을 펴주는 모듈 사용 여부
                    # 일반적인 평면 이미지라면 False로 설정합니다.
                    use_doc_unwarping=False,

                    # 텍스트 라인의 방향(가로/세로)을 감지할지 여부
                    # True로 설정하여 세로 쓰기 텍스트도 잘 인식하도록 합니다.
                    use_textline_orientation=True,

                    # 실행할 장치 설정 (gpu:0 또는 cpu)
                    # GPU가 없다면 자동으로 CPU 모드로 동작하지만, 명시적으로 'cpu'로 설정할 수도 있습니다.
                    device="gpu:0",
                )
    return _ocr_instance


def run_ocr(img_path: str, output_dir: str = "output"):
    """
    이미지에서 텍스트 인식을 수행합니다.
    
    Args:
        img_path: 결제 화면 이미지 경로
        output_dir: 결과 저장 폴더
    
    Returns:
        OCR 결과 JSON 파일 경로
    """
    img_path = Path(img_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    result = _get_ocr().predict(str(img_path))

    for res in result:
        res.save_to_img(str(output_dir))
        res.save_to_json(str(output_dir))

    json_output = output_dir / f"{img_path.stem}_res.json"
    return str(json_output)


# CLI 실행
if __name__ == "__main__":
    _default_img_path = "../tests/fixtures/결제2.png"  # 테스트용 기본 경로
    input_path = sys.argv[1] if len(sys.argv) > 1 else _default_img_path
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    run_ocr(input_path, output_dir)

