# -*- coding: utf-8 -*-
"""
Order list reader utilities.
"""

from typing import List, Dict, Any

from core.korean_datetime import format_date_for_tts


def build_order_list_read_tts(orders: List[Dict[str, Any]]) -> str:
    if not orders:
        return "주문 목록이 비어 있어요."

    total_count = len(orders)
    max_read = 4

    lines = []
    for idx, order in enumerate(orders[:max_read], start=1):
        title = order.get("title") or "상품"
        ordered_at = format_date_for_tts(order.get("ordered_at") or order.get("orderedAt") or "")
        status = order.get("status") or ""
        total_price = order.get("total_price") or ""

        parts = [f"{idx}번 {title}"]
        if ordered_at:
            parts.append(f"주문일 {ordered_at}")
        if status:
            parts.append(f"상태 {status}")
        if total_price:
            parts.append(f"가격 {total_price}")
        lines.append(". ".join(parts))

    intro = f"주문 목록에 {total_count}건이 있어요. 주요 주문을 알려드릴게요."
    tts_text = intro + " " + ". ".join(lines) + "."

    if total_count > max_read:
        remain = total_count - max_read
        tts_text += f" 나머지 {remain}건도 읽어드릴까요?"

    tts_text += " 특정 주문을 보려면 'N번째 주문 상세보기'라고 말씀해 주세요."
    return tts_text
