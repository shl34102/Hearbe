# -*- coding: utf-8 -*-
"""
Login/authorization page presenter helpers.
"""

from typing import Optional

from services.llm.sites.site_manager import get_page_type, get_site_manager


def _page_label(page_type: str) -> Optional[str]:
    return {
        "home": "홈",
        "search": "검색",
        "product": "상품",
        "cart": "장바구니",
        "checkout": "결제",
        "order": "주문",
    }.get(page_type)


def build_login_success_tts(current_url: str) -> str:
    site = get_site_manager().get_site_by_url(current_url)
    site_name = site.name if site and site.name else ""
    page_type = get_page_type(current_url)
    label = _page_label(page_type)
    if label:
        prefix = f"{site_name} " if site_name else ""
        return f"로그인 완료되었습니다. {prefix}{label} 페이지로 이동했습니다."
    return "로그인 완료되었습니다. 페이지가 이동했습니다."


def build_login_autofill_success_tts(current_url: str) -> str:
    """TTS for successful login via browser autofill."""
    site = get_site_manager().get_site_by_url(current_url)
    site_name = site.name if site and site.name else ""
    page_type = get_page_type(current_url)
    label = _page_label(page_type)
    if label:
        prefix = f"{site_name} " if site_name else ""
        return f"자동 로그인되었습니다. {prefix}{label} 페이지로 이동했습니다."
    return "자동 로그인되었습니다. 페이지가 이동했습니다."


def build_login_guidance_tts(active_method: Optional[str] = None) -> str:
    return (
        "현재는 이메일 로그인 페이지입니다. "
        "이메일로 로그인 하시려면 이메일과 비밀번호를 불러주세요. "
        "전화번호로 로그인 하시려면 전화번호로 로그인 하신다고 말씀해 주세요."
    )


def build_captcha_prompt_tts() -> str:
    return (
        "보안 캡차 인증이 필요합니다. 화면을 보고 '다시' 버튼을 눌러 주세요. "
        "그리고 보안 문자를 입력해 주세요."
    )
