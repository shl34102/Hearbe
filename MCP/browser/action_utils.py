"""
브라우저 액션 유틸리티

click_text 등 공통 브라우저 액션 로직을 제공합니다.
MCP 서버와 테스트 API 서버에서 공통으로 사용합니다.
"""

from typing import List, Optional, Dict, Any
from playwright.async_api import Page, Frame


# =============================================================================
# 액션 용어 매핑 (일반적인 UI 용어 → 다양한 표현)
# =============================================================================

GENERIC_ACTIONS = {
    "login": [
        "로그인", "로그인하기", "로그인 하기",
        "Sign in", "Sign In", "Log in", "Log In", "Login",
    ],
    "signup": [
        "회원가입", "가입",
        "Sign up", "Sign Up", "Register", "Join", "Create account", "Create Account",
    ],
    "cart": [
        "장바구니", "카트",
        "Cart", "Basket", "My Cart",
    ],
    "buy": [
        "구매", "바로구매", "구매하기",
        "Buy", "Buy now", "Purchase",
    ],
    "checkout": [
        "결제", "결제하기", "주문", "주문하기",
        "Checkout", "Check out", "Place order", "Pay", "Pay now",
    ],
}


def _normalize(text: str) -> str:
    """텍스트 정규화 (소문자, 공백 제거)"""
    return text.strip().casefold()


def get_action_terms(text: str) -> List[str]:
    """
    입력 텍스트에 대한 관련 액션 용어 목록 반환
    
    예: "로그인" → ["로그인", "로그인하기", "Sign in", ...]
    """
    if not text or not text.strip():
        return []
    
    lowered = _normalize(text)
    terms: List[str] = []
    
    for action_terms in GENERIC_ACTIONS.values():
        for term in action_terms:
            if _normalize(term) in lowered:
                for candidate in action_terms:
                    if candidate not in terms:
                        terms.append(candidate)
                break
    
    return terms


# =============================================================================
# click_text 구현
# =============================================================================

async def _try_click(locator) -> bool:
    """로케이터에서 첫 요소 클릭 시도"""
    try:
        if await locator.count() > 0:
            await locator.first.click(timeout=5000)
            return True
    except Exception:
        pass
    return False


async def click_text_in_frame(frame: Frame, text: str) -> Optional[str]:
    """
    단일 프레임에서 텍스트로 요소 클릭 시도
    
    Args:
        frame: Playwright Frame
        text: 찾을 텍스트
    
    Returns:
        성공 시 결과 메시지, 실패 시 None
    """
    # 1. 버튼 역할로 찾기
    if await _try_click(frame.get_by_role("button", name=text)):
        return f"버튼 클릭: {text}"
    
    # 2. 링크 역할로 찾기
    if await _try_click(frame.get_by_role("link", name=text)):
        return f"링크 클릭: {text}"
    
    # 3. 텍스트로 찾기 (정확 매칭)
    if await _try_click(frame.get_by_text(text, exact=True)):
        return f"텍스트 클릭 (정확): {text}"
    
    # 4. 텍스트로 찾기 (부분 매칭)
    if await _try_click(frame.get_by_text(text)):
        return f"텍스트 클릭 (부분): {text}"
    
    # 5. 다양한 속성 셀렉터로 찾기
    selectors = [
        f"[aria-label*='{text}']",
        f"[title*='{text}']",
        f"input[value*='{text}']",
    ]
    for selector in selectors:
        try:
            locator = frame.locator(selector)
            if await _try_click(locator):
                return f"셀렉터 클릭: {text}"
        except Exception:
            continue
    
    return None


async def click_text(page: Page, text: str) -> Dict[str, Any]:
    """
    페이지에서 텍스트로 요소 클릭
    
    모든 프레임에서 순차적으로 시도하며, 일반 액션 용어도 확장하여 검색합니다.
    
    Args:
        page: Playwright Page
        text: 찾을 텍스트
    
    Returns:
        {"success": True/False, "result": str, "error": str (실패시)}
    """
    # 관련 액션 용어 확장
    terms = get_action_terms(text)
    if text not in terms:
        terms = [text] + terms
    
    # 모든 프레임에서 시도
    for frame in page.frames:
        for term in terms:
            result = await click_text_in_frame(frame, term)
            if result:
                return {"success": True, "result": result}
    
    return {
        "success": False, 
        "error": f"텍스트를 찾을 수 없음: {text}"
    }


# =============================================================================
# get_visible_buttons 구현
# =============================================================================

async def get_visible_buttons(page: Page, max_items: int = 200) -> List[Dict[str, Any]]:
    """
    페이지에서 보이는 버튼 요소들 가져오기
    
    Args:
        page: Playwright Page
        max_items: 최대 항목 수
    
    Returns:
        [{"class": str, "text": str, "dataKey": str, "frameUrl": str}, ...]
    """
    selector_script = """
      (maxItems, includePadKeys) => {
        const selectors = [
          "button",
          "a[role='button']",
          "input[type='button']",
          "input[type='submit']",
        ];
        if (includePadKeys) {
          selectors.push("a.pad-key");
        }
        const nodes = Array.from(document.querySelectorAll(selectors.join(",")));
        const visible = [];
        for (const el of nodes) {
          if (visible.length >= maxItems) break;
          const rect = el.getBoundingClientRect();
          if (!rect || rect.width === 0 || rect.height === 0) continue;
          const style = window.getComputedStyle(el);
          if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") continue;
          const text = (el.innerText || el.value || el.getAttribute("aria-label") || "").trim();
          visible.push({
            class: (el.className || "").toString(),
            text,
            dataKey: el.getAttribute("data-key") || "",
          });
        }
        return visible;
      }
    """
    
    results = []
    remaining = max_items
    
    for frame in page.frames:
        if remaining <= 0:
            break
        include_pad_keys = "coupang.com" in frame.url
        try:
            items = await frame.evaluate(selector_script, remaining, include_pad_keys)
        except Exception:
            continue
        if not items:
            continue
        for item in items:
            if remaining <= 0:
                break
            item["frameUrl"] = frame.url
            results.append(item)
            remaining -= 1
    
    return results
