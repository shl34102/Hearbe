#!/usr/bin/env python3
"""
버튼 정보를 UTF-8로 제대로 저장하는 스크립트
"""
import requests
import json
from pathlib import Path

# buttons directory (same as script location)
buttons_dir = Path(__file__).parent
buttons_dir.mkdir(exist_ok=True)

# API에서 버튼 정보 가져오기
response = requests.get("http://localhost:8000/buttons")
data = response.json()

# 현재 URL 가져오기
url_response = requests.get("http://localhost:8000/url")
current_url = url_response.json().get("url", "")

# 파일명 결정
if "memberJoin" in current_url or "signup" in current_url:
    filename = "coupang_signup_buttons.json"
elif "login" in current_url:
    filename = "coupang_login_buttons.json"
elif "search" in current_url:
    filename = "coupang_search_buttons.json"
elif "vp/products" in current_url or "/products/" in current_url:
    filename = "coupang_product_buttons.json"
elif "cart" in current_url:
    filename = "coupang_cart_buttons.json"
elif "checkout" in current_url:
    filename = "coupang_checkout_buttons.json"
elif "order/list" in current_url:
    filename = "coupang_orderlist_buttons.json"
elif "shiptrack" in current_url:
    filename = "coupang_shiptrack_buttons.json"
elif "/order/" in current_url and "order/list" not in current_url:
    filename = "coupang_orderdetail_buttons.json"
elif "universal-flow" in current_url:
    filename = "coupang_return_buttons.json"
else:
    filename = "coupang_main_buttons.json"

# UTF-8로 저장
output_path = buttons_dir / filename
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"[OK] Saved: {output_path}")
print(f"[URL] {current_url}")
print(f"[COUNT] {data.get('count', 0)}")
