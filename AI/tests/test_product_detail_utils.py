# -*- coding: utf-8 -*-

from api.ws.feedback.product_detail_utils import (
    build_product_payload,
    extract_coupang_product_number,
)


def test_extract_coupang_product_number_from_kv() -> None:
    detail = {
        "coupang_product_info_kv": {
            "쿠팡상품번호": "7689270513 - 20972233691",
        }
    }
    assert extract_coupang_product_number(detail) == "7689270513 - 20972233691"


def test_extract_coupang_product_number_from_info_lines() -> None:
    detail = {
        "coupang_product_info": [
            "소비기한(또는 유통기한): 2026-12-15 이거나 그 이후인 상품",
            "쿠팡상품번호: 7689270513 - 20972233691",
        ]
    }
    assert extract_coupang_product_number(detail) == "7689270513 - 20972233691"


def test_build_product_payload_requires_name_and_category_path() -> None:
    detail = {
        "name": "탐사 샘물, 500ml, 40개",
        "category_path": [
            "식품",
            "생수/음료",
            "생수",
        ],
        "coupang_product_info_kv": {
            "쿠팡상품번호": "7689270513 - 20972233691",
        },
    }
    payload = build_product_payload(detail)
    assert payload is not None
    assert payload["name"] == "탐사 샘물, 500ml, 40개"
    assert payload["category_path"] == ["식품", "생수/음료", "생수"]
    assert payload["coupang_product_number"] == "7689270513 - 20972233691"


def test_build_product_payload_returns_none_when_missing_category() -> None:
    detail = {
        "name": "탐사 샘물, 500ml, 40개",
        "category_path": [],
    }
    assert build_product_payload(detail) is None

