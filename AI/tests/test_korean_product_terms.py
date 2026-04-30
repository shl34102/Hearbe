# -*- coding: utf-8 -*-
from core.korean_product_terms import format_product_terms_for_tts


def test_format_kcal() -> None:
    assert format_product_terms_for_tts("100kcal") == "100칼로리"
    assert format_product_terms_for_tts("100 kcal") == "100 칼로리"
    assert format_product_terms_for_tts("KCAL") == "칼로리"


def test_format_units() -> None:
    assert format_product_terms_for_tts("1000 g") == "1000그램"
    assert format_product_terms_for_tts("1,000g") == "1,000그램"
    assert format_product_terms_for_tts("1 kg") == "1킬로그램"
    assert format_product_terms_for_tts("25mm") == "25밀리미터"
    assert format_product_terms_for_tts("10 cm") == "10센티미터"
    assert format_product_terms_for_tts("500ml") == "500밀리리터"
    assert format_product_terms_for_tts("1 L") == "1리터"
    assert format_product_terms_for_tts("2\u33a1") == "2제곱미터"


def test_format_haccp() -> None:
    assert format_product_terms_for_tts("HACCP 인증") == "해썹 인증"
    assert format_product_terms_for_tts("H.A.C.C.P") == "해썹"
    assert format_product_terms_for_tts("KS 인증") == "케이에스 인증"
    assert format_product_terms_for_tts("KC 인증") == "케이씨 인증"
    assert format_product_terms_for_tts("ISO 9001") == "아이에스오 9001"


def test_format_bonus_and_mixed_pack() -> None:
    assert format_product_terms_for_tts("1+1 행사") == "원 플러스 원 행사"
    assert format_product_terms_for_tts("2 + 1 구성") == "투 플러스 원 구성"
    assert format_product_terms_for_tts("500ml x 2") == "오백 밀리리터 두개"
    assert format_product_terms_for_tts("1L×3") == "일리터 세개"


def test_format_size_terms() -> None:
    assert format_product_terms_for_tts("XL") == "엑스라지"
    assert format_product_terms_for_tts("2XL") == "투 엑스라지"
    assert format_product_terms_for_tts("2xl") == "투 엑스라지"
    assert format_product_terms_for_tts("XXL") == "투 엑스라지"
    assert format_product_terms_for_tts("XXXL") == "쓰리 엑스라지"
