"""
Order list action handler.

Handles order detail navigation from order list page using session context.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
import re
import time
from urllib.parse import urlparse

from core.interfaces import MCPCommand, LLMResponse, SessionState
from core.korean_datetime import format_date_for_tts
from core.korean_numbers import extract_ordinal_index, parse_korean_number
from services.llm.sites.site_manager import get_page_type

DETAIL_KEYWORDS = (
    "상세",
    "상세보기",
    "주문 상세",
    "주문상세",
    "상세로",
    "조회",
    "주문 조회",
    "주문조회",
    "확인",
    "내역",
    "주문 내역",
    "주문내역",
    "보기",
    "열어",
    "들어가",
)

READ_KEYWORDS = (
    "주문 목록",
    "주문목록",
    "주문 내역",
    "주문내역",
    "주문 리스트",
    "주문리스트",
    "읽어",
    "알려",
    "보여",
    "확인",
    "조회",
)

_READ_COUNT_RE = re.compile(r"(\d+)\s*(개|건)\s*(만)?")
_READ_COUNT_KO_RE = re.compile(r"([가-힣]+)\s*(개|건)\s*(만)?")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def _is_coupang_orderlist_url(url: str) -> bool:
    """
    Guard: only handle "order list" actions on Coupang order-list pages.

    We have multiple "orderlist" page_types (platform/other sites). Without this guard,
    "N번째 주문 상세보기" can click a product title link and drift to a product page.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = (parsed.netloc or "").lower()
    if not host.endswith("coupang.com"):
        return False
    path = parsed.path or ""
    # Expected: https://mc.coupang.com/ssr/desktop/order/list
    return "/ssr/desktop/order/list" in path


def _is_valid_order_detail_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = (parsed.netloc or "").lower()
    if not host.endswith("coupang.com"):
        return False
    # Some links may include a trailing slash. Keep this permissive to avoid dropping all items.
    return bool(re.search(r"/ssr/desktop/order/\d+/?$", parsed.path or ""))


def _find_by_title(items: List[Dict[str, Any]], text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    norm = _normalize(text)
    if not norm:
        return None
    for item in items:
        title = str(item.get("title") or "")
        if not title:
            continue
        title_norm = _normalize(title)
        if not title_norm:
            continue
        if norm in title_norm or title_norm in norm:
            return item
    return None


def _build_detail_commands(item: Dict[str, Any]) -> List[MCPCommand]:
    selector = item.get("detail_selector")
    url = item.get("detail_url")
    title = item.get("title") or ""

    commands: List[MCPCommand] = []
    # Prefer URL navigation when we have a valid order-detail URL.
    # It's less error-prone than clicking text/selectors that might match a product link.
    if url and _is_valid_order_detail_url(str(url)):
        commands.append(
            MCPCommand(
                tool_name="goto",
                arguments={"url": url},
                description="go to order detail",
            )
        )
    elif selector:
        commands.append(
            MCPCommand(
                tool_name="click",
                arguments={"selector": selector},
                description="open order detail",
            )
        )
    elif title:
        commands.append(
            MCPCommand(
                tool_name="click_text",
                arguments={"text": str(title)},
                description="click order title",
            )
        )

    if commands:
        commands.append(
            MCPCommand(
                tool_name="wait",
                arguments={"ms": 1500},
                description="wait for order detail page",
            )
        )
    return commands


def _extract_read_limit(text: str) -> tuple[Optional[int], bool]:
    if not text:
        return None, False

    match = _READ_COUNT_RE.search(text)
    if match:
        value = int(match.group(1))
        if value > 0:
            return value, bool(match.group(3))

    match = _READ_COUNT_KO_RE.search(text)
    if match:
        value = parse_korean_number(match.group(1))
        if value and value > 0:
            return value, bool(match.group(3))

    return None, False


def _build_order_list_summary_text(
    items: List[Dict[str, Any]],
    limit: Optional[int] = None,
    suppress_more_prompt: bool = False,
) -> str:
    if not items:
        return "주문 목록이 비어 있어요."

    total_count = len(items)
    max_read = 4 if limit is None else min(max(limit, 1), total_count)
    lines = []
    for idx, order in enumerate(items[:max_read], start=1):
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

    if total_count > max_read and not suppress_more_prompt:
        remain = total_count - max_read
        tts_text += f" 나머지 {remain}건도 읽어드릴까요?"

    tts_text += " 특정 주문을 보려면 'N번째 주문 상세보기'라고 말씀해 주세요."
    return tts_text


def _is_affirmative(text: str) -> bool:
    keywords = [
        "네", "응", "예", "그래", "그래요", "맞아", "맞아요", "어",
        "읽어", "읽어줘", "읽어주세요", "읽어줄래",
    ]
    return any(word in text for word in keywords)


def _is_negative(text: str) -> bool:
    keywords = [
        "아니", "아니요", "괜찮아", "괜찮아요", "싫어", "됐어", "필요없어", "필요 없어",
    ]
    return any(word in text for word in keywords)


def handle_order_list_action(user_text: str, session: Optional[SessionState]) -> Optional[LLMResponse]:
    if not session:
        return None
    # Allow handling even when context is empty; we'll set pending extraction if needed.
    if session.context is None:
        session.context = {}
    current_url = session.current_url or ""
    if not current_url or get_page_type(current_url) != "orderlist":
        return None
    if not _is_coupang_orderlist_url(current_url):
        return None

    text = (user_text or "").strip()
    if not text:
        return None

    # Order list extraction is async (auto-extract on page change). If the user asks for an
    # order detail by ordinal before extraction finishes, queue the intent and trigger extract.
    ordinal_index = extract_ordinal_index(text)
    has_detail_intent = any(keyword in text for keyword in DETAIL_KEYWORDS)
    if (ordinal_index is not None or has_detail_intent) and not session.context.get("order_list"):
        session.context["pending_order_detail_open"] = {
            "index": ordinal_index,
            "text": text[:200],
            "ts": time.time(),
        }
        return LLMResponse(
            text="주문 목록을 먼저 불러온 뒤 선택한 주문의 상세 페이지로 이동할게요. 잠시만 기다려 주세요.",
            commands=[
                MCPCommand(
                    tool_name="wait_for_selector",
                    arguments={
                        # Exclude `/list` to avoid matching breadcrumb links and extracting too early.
                        "selector": "a[href*='/ssr/desktop/order/']:not([href*='/ssr/desktop/order/list'])",
                        "state": "visible",
                        "timeout": 20000,
                    },
                    description="wait for order list items",
                ),
                MCPCommand(
                    tool_name="wait",
                    arguments={"ms": 800},
                    description="wait for order list items to stabilize",
                ),
                MCPCommand(
                    tool_name="extract_order_list",
                    arguments={},
                    description="extract order list (pending order detail open)",
                ),
                MCPCommand(
                    tool_name="wait",
                    arguments={"ms": 1200},
                    description="wait for order list extraction",
                ),
            ],
            requires_flow=False,
            flow_type=None,
        )
    order_list = session.context.get("order_list")
    items: List[Dict[str, Any]] = []
    if isinstance(order_list, dict):
        raw = order_list.get("orders") or order_list.get("items") or order_list.get("order_list")
        if isinstance(raw, list):
            items = [item for item in raw if isinstance(item, dict)]
    elif isinstance(order_list, list):
        items = [item for item in order_list if isinstance(item, dict)]

    # Filter out non-order entries (e.g., "마이쿠팡" nav items) to keep indexing stable.
    items = [
        item
        for item in items
        if _is_valid_order_detail_url(str(item.get("detail_url") or ""))
    ]

    if not items:
        return None
    title_match = _find_by_title(items, text)
    has_read_intent = any(keyword in text for keyword in READ_KEYWORDS)

    prompt_pending = bool(session.context.get("order_list_prompt_pending"))
    if prompt_pending:
        read_limit, read_only = _extract_read_limit(text)
        if read_limit is not None:
            session.context["order_list_prompt_pending"] = False
            summary = _build_order_list_summary_text(
                items,
                limit=read_limit,
                suppress_more_prompt=read_only,
            )
            return LLMResponse(
                text=summary,
                commands=[],
                requires_flow=False,
                flow_type=None,
            )
        if _is_affirmative(text):
            session.context["order_list_prompt_pending"] = False
            summary = _build_order_list_summary_text(items)
            return LLMResponse(
                text=summary,
                commands=[],
                requires_flow=False,
                flow_type=None,
            )
        if _is_negative(text):
            session.context["order_list_prompt_pending"] = False
            return LLMResponse(
                text="알겠습니다. 필요하신 내용을 말씀해 주세요.",
                commands=[],
                requires_flow=False,
                flow_type=None,
            )

    # ordinal 또는 상품명 매칭 시 → 상세 이동 우선
    target = None
    if ordinal_index is not None and 0 <= ordinal_index < len(items):
        target = items[ordinal_index]
    if target is None:
        target = title_match or _find_by_title(items, text)
    # ordinal/상품명 없이 상세 의도만 있으면 → 첫 번째 주문을 기본 타겟으로
    if target is None and has_detail_intent and items:
        target = items[0]

    # 타겟이 있으면 바로 상세 이동
    if target:
        commands = _build_detail_commands(target)
        if commands:
            session.context["order_list_prompt_pending"] = False
            title = target.get("title") or ""
            label = title or "선택한 주문"
            return LLMResponse(
                text=f"{label} 상세로 이동합니다.",
                commands=commands,
                requires_flow=False,
                flow_type=None,
            )

    # 타겟 없이 읽기 의도만 있으면 → 목록 요약
    if has_read_intent and not has_detail_intent:
        session.context["order_list_prompt_pending"] = False
        read_limit, read_only = _extract_read_limit(text)
        summary = _build_order_list_summary_text(
            items,
            limit=read_limit,
            suppress_more_prompt=read_only,
        )
        return LLMResponse(
            text=summary,
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    if not has_read_intent and not has_detail_intent:
        return None

    return None


__all__ = ["handle_order_list_action"]
