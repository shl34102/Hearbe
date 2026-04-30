"""
OCRService 유닛 테스트

담당: 김재환
"""

import pytest
import base64
from unittest.mock import AsyncMock, patch, MagicMock

from services.ocr import (
    OCRService,
    OCRResult,
    OCRType,
    KeypadLayout,
    KeypadButton,
    BoundingBox,
)


class TestOCRService:
    """OCRService 테스트"""

    # ---- 초기화 테스트 ----

    def test_init(self):
        """서비스 초기화"""
        service = OCRService(model_name="trocr-base-printed", device="cpu")

        assert service._model_name == "trocr-base-printed"
        assert service._device == "cpu"
        assert service._model is None

    def test_init_default(self):
        """기본값 초기화"""
        service = OCRService()

        assert service._model_name == "trocr-base-printed"
        assert service._device == "cuda"

    @pytest.mark.asyncio
    async def test_initialize(self):
        """모델 초기화"""
        service = OCRService()
        await service.initialize()
        # TODO: 실제 모델 로딩 Mock 테스트

    # ---- 이미지 인식 테스트 ----

    @pytest.mark.asyncio
    async def test_recognize_image(self):
        """이미지 텍스트 인식"""
        service = OCRService()

        # 가짜 이미지 데이터
        fake_image = base64.b64encode(b"fake_image_data").decode()

        result = await service.recognize_image(fake_image)

        assert isinstance(result, OCRResult)
        assert result.ocr_type == OCRType.TEXT

    @pytest.mark.asyncio
    async def test_recognize_image_invalid_base64(self):
        """잘못된 Base64 이미지"""
        service = OCRService()

        result = await service.recognize_image("invalid_base64!!!")

        assert result.confidence == 0.0

    # ---- 키패드 인식 테스트 ----

    @pytest.mark.asyncio
    async def test_detect_keypad(self):
        """키패드 인식"""
        service = OCRService()

        fake_image = base64.b64encode(b"keypad_image").decode()

        keypad = await service.detect_keypad(fake_image)

        assert isinstance(keypad, KeypadLayout)
        assert len(keypad.buttons) > 0

    @pytest.mark.asyncio
    async def test_keypad_get_position(self):
        """키패드 버튼 위치 조회"""
        service = OCRService()

        fake_image = base64.b64encode(b"keypad_image").decode()

        keypad = await service.detect_keypad(fake_image)

        # 0-9 버튼 위치 확인
        for digit in "0123456789":
            position = keypad.get_position(digit)
            if position:  # 일부는 없을 수 있음
                assert isinstance(position, tuple)
                assert len(position) == 2

    @pytest.mark.asyncio
    async def test_keypad_to_dict(self):
        """키패드 딕셔너리 변환"""
        service = OCRService()

        fake_image = base64.b64encode(b"keypad_image").decode()

        keypad = await service.detect_keypad(fake_image)
        result = keypad.to_dict()

        assert result["type"] == "keypad"
        assert "positions" in result

    # ---- CAPTCHA 인식 테스트 ----

    @pytest.mark.asyncio
    async def test_recognize_captcha(self):
        """CAPTCHA 인식"""
        service = OCRService()

        fake_image = base64.b64encode(b"captcha_image").decode()

        text = await service.recognize_captcha(fake_image)

        assert isinstance(text, str)

    # ---- PIN 입력 시퀀스 테스트 ----

    @pytest.mark.asyncio
    async def test_get_keypad_click_sequence(self):
        """PIN 클릭 시퀀스 생성"""
        service = OCRService()

        fake_image = base64.b64encode(b"keypad_image").decode()

        sequence = await service.get_keypad_click_sequence(fake_image, "1234")

        # 4자리 PIN이므로 최대 4개의 좌표
        assert len(sequence) <= 4

        for pos in sequence:
            assert isinstance(pos, tuple)
            assert len(pos) == 2
            assert isinstance(pos[0], int)
            assert isinstance(pos[1], int)

    @pytest.mark.asyncio
    async def test_get_keypad_click_sequence_invalid_digit(self):
        """키패드에 없는 문자 입력"""
        service = OCRService()

        fake_image = base64.b64encode(b"keypad_image").decode()

        # 'A'는 키패드에 없음
        sequence = await service.get_keypad_click_sequence(fake_image, "12A4")

        # 'A'를 제외한 3개만 반환
        assert len(sequence) == 3

    # ---- 리소스 정리 테스트 ----

    @pytest.mark.asyncio
    async def test_close(self):
        """리소스 정리"""
        service = OCRService()
        await service.close()

        assert service._model is None
        assert service._processor is None


class TestBoundingBox:
    """BoundingBox 모델 테스트"""

    def test_center(self):
        """중심점 계산"""
        bbox = BoundingBox(x=100, y=200, width=50, height=40)

        center = bbox.center

        assert center == (125, 220)

    def test_center_zero(self):
        """원점 박스"""
        bbox = BoundingBox(x=0, y=0, width=100, height=100)

        center = bbox.center

        assert center == (50, 50)


class TestKeypadLayout:
    """KeypadLayout 모델 테스트"""

    def test_get_position_found(self):
        """버튼 위치 찾기"""
        buttons = [
            KeypadButton(
                value="5",
                bbox=BoundingBox(x=100, y=100, width=50, height=50),
                confidence=0.9
            )
        ]

        keypad = KeypadLayout(buttons=buttons)

        position = keypad.get_position("5")

        assert position == (125, 125)

    def test_get_position_not_found(self):
        """없는 버튼"""
        keypad = KeypadLayout(buttons=[])

        position = keypad.get_position("X")

        assert position is None

    def test_to_dict(self):
        """딕셔너리 변환"""
        buttons = [
            KeypadButton(
                value="1",
                bbox=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.95
            )
        ]

        keypad = KeypadLayout(buttons=buttons, rows=4, cols=3)
        result = keypad.to_dict()

        assert result["type"] == "keypad"
        assert result["rows"] == 4
        assert result["cols"] == 3
        assert "1" in result["positions"]
        assert result["positions"]["1"]["x"] == 50
        assert result["positions"]["1"]["y"] == 50


class TestOCRResult:
    """OCRResult 모델 테스트"""

    def test_to_dict_text(self):
        """텍스트 결과 변환"""
        result = OCRResult(
            ocr_type=OCRType.TEXT,
            text="Hello World",
            confidence=0.95
        )

        data = result.to_dict()

        assert data["type"] == "text"
        assert data["text"] == "Hello World"
        assert data["confidence"] == 0.95

    def test_to_dict_keypad(self):
        """키패드 결과 변환"""
        keypad = KeypadLayout(buttons=[])

        result = OCRResult(
            ocr_type=OCRType.KEYPAD,
            confidence=0.9,
            keypad=keypad
        )

        data = result.to_dict()

        assert data["type"] == "keypad"
        assert "keypad" in data
