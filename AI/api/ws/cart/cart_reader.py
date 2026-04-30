# -*- coding: utf-8 -*-
"""
Cart reader utilities.
"""

from typing import List, Dict


def build_cart_read_tts(
    items: List[Dict],
    summary: Dict[str, str]
) -> str:
    if not items:
        return "장바구니가 비어 있어요."

    total_count = len(items)
    selected_count = sum(1 for item in items if item.get("selected") is True)

    def _normalize_quantity(value: str | int | None) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        return f"{text}개" if text.isdigit() else text

    lines = []
    max_read = 4
    for idx, item in enumerate(items[:max_read]):
        name = item.get("name") or "상품"
        option = item.get("option") or ""
        arrival = item.get("arrival") or ""
        price = item.get("price") or ""
        quantity = _normalize_quantity(item.get("quantity") or "")
        selected = item.get("selected")
        parts = [f"{idx + 1}번 {name}"]
        if selected is True:
            parts.append("현재 선택됨")
        if option:
            parts.append(f"옵션 {option}")
        if arrival:
            parts.append(arrival)
        if price:
            parts.append(f"가격 {price}")
        if quantity:
            parts.append(f"수량 {quantity}")
        lines.append(". ".join(parts))

    intro = f"장바구니에 상품 {total_count}개가 있어요."
    if selected_count:
        intro += f" 현재 선택된 상품은 {selected_count}개입니다."
    intro += " 주요 상품을 알려드릴게요."

    tts_text = intro + " " + ". ".join(lines) + "."

    if total_count > max_read:
        remain = total_count - max_read
        tts_text += f" 나머지 {remain}개도 읽어드릴까요?"

    total_product_price = summary.get("total_product_price") or ""
    total_instant_discount = summary.get("total_instant_discount") or summary.get("instant_discount") or ""
    shipping_fee = summary.get("shipping_fee") or ""
    final_total = summary.get("total_price") or summary.get("final_order_price") or ""
    if total_product_price or total_instant_discount or shipping_fee or final_total:
        tts_text += " 총액 정보입니다."
        if total_product_price:
            tts_text += f" 총 상품 가격 {total_product_price}."
        if total_instant_discount:
            tts_text += f" 총 즉시할인 {total_instant_discount}."
        if shipping_fee:
            tts_text += f" 총 배송비 {shipping_fee}."
        if final_total:
            tts_text += f" 최종 결제 금액 {final_total}."

    rocket_blocked = summary.get("rocket_fresh_blocked") is True
    rocket_current = summary.get("rocket_fresh_current") or ""
    rocket_threshold = summary.get("rocket_fresh_threshold") or ""
    rocket_remaining = summary.get("rocket_fresh_remaining") or ""
    if rocket_blocked or rocket_remaining:
        tts_text += " 로켓프레시 최소 결제 금액 기준이 있습니다."
        if rocket_current:
            tts_text += f" 현재 {rocket_current}."
        if rocket_threshold:
            tts_text += f" 기준 {rocket_threshold}."
        if rocket_remaining:
            tts_text += f" {rocket_remaining} 부족합니다."
        tts_text += " 로켓프레시 상품을 더 담을까요, 아니면 해당 상품을 제외할까요?"

    return tts_text
