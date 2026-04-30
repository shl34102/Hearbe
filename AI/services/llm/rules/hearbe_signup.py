# -*- coding: utf-8 -*-
"""
Hearbe signup parsing rule.
"""

from __future__ import annotations

import re
from typing import Optional

from . import BaseRule, RuleResult
from ..context.context_rules import (
    build_click_command,
    build_fill_command,
    build_wait_command,
    build_wait_for_selector_command,
)
from ..sites.site_manager import get_page_type, get_selector


class HearbeSignupRule(BaseRule):
    """Handle Hearbe signup page input and actions."""

    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not text:
            return None
        if get_page_type(current_url) != "signup":
            return None
        if not current_site or getattr(current_site, "site_id", "") != "hearbe":
            return None

        if _is_terms_read_request(text):
            return RuleResult(
                matched=True,
                commands=[],
                response_text=_build_terms_text(),
                rule_name="hearbe_signup_terms",
            )

        normalized = _normalize_text(text)
        fields = _extract_signup_fields(normalized)

        want_duplicate_check = _contains_any(
            normalized,
            ("중복확인", "중복 확인", "아이디 중복", "아이디 확인", "확인완료", "확인됨"),
        )
        want_terms_agree = _contains_any(normalized, ("약관 동의", "약관에 동의", "동의", "체크"))
        want_submit = _is_submit_intent(normalized)

        selectors = _resolve_selectors(current_url, current_site)
        commands = []

        if fields.get("username") and selectors.get("username_input"):
            commands += _fill_with_wait(selectors["username_input"], fields["username"], "아이디 입력")
        if fields.get("password") and selectors.get("password_input"):
            commands += _fill_with_wait(selectors["password_input"], fields["password"], "비밀번호 입력")
        if fields.get("password_confirm") and selectors.get("password_confirm_input"):
            commands += _fill_with_wait(
                selectors["password_confirm_input"],
                fields["password_confirm"],
                "비밀번호 확인 입력",
            )
        if fields.get("name") and selectors.get("name_input"):
            commands += _fill_with_wait(selectors["name_input"], fields["name"], "이름 입력")
        if fields.get("email") and selectors.get("email_input"):
            commands += _fill_with_wait(selectors["email_input"], fields["email"], "이메일 입력")
        if fields.get("phone") and selectors.get("phone_input"):
            commands += _fill_with_wait(selectors["phone_input"], fields["phone"], "휴대폰 번호 입력")

        if want_duplicate_check and selectors.get("username_check_button"):
            commands.append(build_click_command(selectors["username_check_button"], "아이디 중복확인"))
            if selectors.get("modal_confirm"):
                commands.append(
                    build_wait_for_selector_command(
                        selectors["modal_confirm"],
                        state="visible",
                        timeout=4000,
                        description="중복확인 모달 대기",
                    )
                )
                commands.append(build_click_command(selectors["modal_confirm"], "중복확인 모달 확인"))

        if want_terms_agree and selectors.get("terms_checkbox"):
            commands.append(build_click_command(selectors["terms_checkbox"], "약관 동의 체크"))

        if want_submit and selectors.get("submit_button"):
            commands.append(build_click_command(selectors["submit_button"], "회원가입 제출"))
            commands.append(build_wait_command(1500, "회원가입 처리 대기"))
            if _is_hearbe_c_signup(current_url) and selectors.get("signup_complete_confirm"):
                commands.append(
                    build_wait_for_selector_command(
                        selectors["signup_complete_confirm"],
                        state="visible",
                        timeout=6000,
                        description="회원가입 완료 모달 대기",
                    )
                )
                commands.append(build_click_command(selectors["signup_complete_confirm"], "회원가입 완료 확인"))

        if not commands:
            return None

        response_text = _build_response_text(
            fields=fields,
            want_duplicate_check=want_duplicate_check,
            want_terms_agree=want_terms_agree,
            want_submit=want_submit,
        )

        return RuleResult(
            matched=True,
            commands=commands,
            response_text=response_text,
            rule_name="hearbe_signup",
        )


def _resolve_selectors(current_url: str, current_site) -> dict:
    def pick(name: str) -> Optional[str]:
        return get_selector(current_url, name) or current_site.get_selector("signup", name)

    return {
        "username_input": pick("username_input"),
        "password_input": pick("password_input"),
        "password_confirm_input": pick("password_confirm_input"),
        "name_input": pick("name_input"),
        "email_input": pick("email_input"),
        "phone_input": pick("phone_input"),
        "terms_checkbox": pick("terms_checkbox"),
        "username_check_button": pick("username_check_button"),
        "submit_button": pick("submit_button"),
        "modal_confirm": pick("modal_confirm"),
        "terms_modal_confirm": pick("terms_modal_confirm"),
        "signup_complete_confirm": pick("signup_complete_confirm"),
    }


def _fill_with_wait(selector: str, value: str, desc: str):
    return [
        build_wait_for_selector_command(
            selector,
            state="visible",
            timeout=8000,
            description=f"{desc} 입력칸 대기",
        ),
        build_fill_command(selector, value, desc),
    ]


def _build_response_text(fields: dict, want_duplicate_check: bool, want_terms_agree: bool, want_submit: bool) -> str:
    if want_submit:
        return "회원가입을 진행합니다."
    if want_duplicate_check and want_terms_agree:
        return "아이디 중복확인과 약관 동의를 진행합니다."
    if want_duplicate_check:
        return "아이디 중복확인을 진행합니다."
    if want_terms_agree:
        return "약관 동의를 진행합니다."
    if fields:
        return "회원가입 정보를 입력합니다."
    return "회원가입을 진행합니다."


def _extract_signup_fields(text: str) -> dict:
    fields = {}

    email = _extract_email(text)
    if email:
        fields["email"] = email

    username = _extract_labeled_alnum(text, ("아이디", "id"), 4, 20)
    if username:
        fields["username"] = username

    password_confirm = _extract_labeled_alnum(
        text,
        ("비밀번호 확인", "비번 확인", "비밀번호 재확인", "비번 재확인", "확인 비밀번호"),
        4,
        32,
    )
    if password_confirm:
        fields["password_confirm"] = password_confirm

    password = _extract_labeled_alnum(
        text,
        ("비밀번호", "비번", "패스워드", "password", "pw"),
        4,
        32,
    )
    if password:
        fields["password"] = password

    name = _extract_labeled_name(text, ("이름", "성명", "name"))
    if name:
        fields["name"] = name

    phone = _extract_phone(text)
    if phone:
        fields["phone"] = phone

    return fields


def _extract_email(text: str) -> Optional[str]:
    normalized = _normalize_email_text(text)
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalized)
    if match:
        return match.group(0)
    return None


def _extract_labeled_alnum(text: str, labels: tuple[str, ...], min_len: int, max_len: int) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?:{label_pattern})\s*(?:[:：]|은|는|이|가)?\s*([A-Za-z0-9\\s]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    value = re.sub(r"\\s+", "", match.group(1))
    return _sanitize_alnum(value, min_len, max_len)


def _extract_labeled_name(text: str, labels: tuple[str, ...]) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?:{label_pattern})\s*(?:[:：]|은|는|이|가)?\s*([가-힣A-Za-z\\s]+)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1).strip()
    value = re.sub(r"\\s+", " ", value)
    if len(value) < 2:
        return None
    return value


def _extract_phone(text: str) -> Optional[str]:
    digits = re.sub(r"\\D", "", text)
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return None


def _sanitize_alnum(value: str, min_len: int, max_len: int) -> Optional[str]:
    if not value:
        return None
    value = re.sub(r"[^A-Za-z0-9]", "", value)
    if len(value) < min_len or len(value) > max_len:
        return None
    return value


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _normalize_email_text(text: str) -> str:
    value = text or ""
    value = value.replace("골뱅이", "@").replace("골뱅", "@").replace("앳", "@").replace("엣", "@")
    value = value.replace("닷컴", ".com").replace("닷넷", ".net")
    value = value.replace("점", ".").replace("쩜", ".").replace("닷", ".").replace("도트", ".")
    value = value.replace("지메일", "gmail").replace("네이버", "naver").replace("다음", "daum")
    return value


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _is_terms_read_request(text: str) -> bool:
    if not text:
        return False
    normalized = _normalize_text(text)
    if "약관" not in normalized:
        return False
    return _contains_any(
        normalized,
        ("읽어", "읽어줘", "읽어 주세요", "내용", "보여줘", "보여 주세요", "알려줘", "설명해줘"),
    )


def _is_submit_intent(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "회원가입" in text or "회원 가입" in text:
        return True
    submit_tokens = (
        "가입해",
        "가입해줘",
        "가입해주세요",
        "가입할게",
        "가입 진행",
        "가입 신청",
        "가입 완료",
        "회원등록",
        "회원 등록",
    )
    if any(token in text for token in submit_tokens):
        return True
    if "signup" in lowered or "sign up" in lowered:
        return True
    return False


def _is_hearbe_c_signup(current_url: str) -> bool:
    if not current_url:
        return False
    return "/c/" in current_url.lower()


def _build_terms_text() -> str:
    return (
        "제1조 (AI 에이전트 서비스 이용 안내)\n"
        "본 서비스는 사용자의 편리한 쇼핑을 위해 AI 에이전트 기술을 활용합니다.\n\n"
        "AI 브라우저 대리 조작: 사용자가 음성으로 명령하면, HearBe의 AI 에이전트가 가상 브라우저를 통해 실제 쇼핑몰 웹사이트를 "
        "사용자를 대신하여 탐색하고 조작합니다. 이는 사용자가 직접 화면을 보고 클릭하는 과정을 AI가 음성 명령에 따라 수행하는 것입니다.\n\n"
        "화면 분석 및 정보 제공: AI는 쇼핑몰의 이미지와 텍스트를 실시간으로 분석하여 사용자에게 음성으로 전달합니다. "
        "이 과정에서 정확한 정보 전달을 위해 화면 캡처 및 텍스트 추출이 이루어질 수 있습니다.\n\n"
        "---------------------------------------------\n\n"
        "제2조 (개인정보 수집 및 이용 항목)\n"
        "서비스 제공을 위해 아래와 같은 정보를 수집합니다. 수집된 정보는 회원 탈퇴 시 또는 법정 보유 기간 종료 시 즉시 파기됩니다.\n\n"
        "1. 시각장애인 사용자 (A형, B형)\n"
        "- 필수 수집 항목: 아이디, 비밀번호, 이름\n"
        "- 선택 수집 항목: 휴대폰 번호\n"
        "- 장애인 복지 카드 확인 정보: 카드사, 카드번호 뒤 4자리, 유효기간 (사용자 맞춤형 UI 제공 목적)\n"
        "- 음성 데이터: 음성 명령 인식 및 처리 (목적 달성 후 즉시 파기)\n\n"
        "2. 일반인 및 보호자 사용자 (C형)\n"
        "- 필수 수집 항목: 아이디, 비밀번호, 이름, 이메일 주소\n"
        "- 원격 제어 정보: 사용자 브라우저 원격 조종을 위한 접속 로그 및 명령 데이터\n\n"
        "---------------------------------------------\n\n"
        "제3조 (결제 보안 및 민감 정보 보호)\n"
        "결제 확인: AI가 사용자를 대신해 결제 단계까지 진입할 수 있으나, 실제 결제 승인은 사용자의 최종 확인(비밀번호 입력 또는 음성 확답)이 있어야만 완료됩니다.\n\n"
        "비밀번호 미저장 원칙: 사용자의 결제 비밀번호는 서비스 내 어떠한 장치나 서버에도 저장되지 않으며, 결제 시마다 사용자가 직접 입력하는 것을 원칙으로 합니다.\n\n"
        "기기 기반 암호화 등록: 복지 카드 정보 등 서비스 이용을 위해 등록한 민감 정보는 서버에 저장되지 않으며, 사용자가 서비스에 접속한 해당 웹 브라우저 및 기기에만 암호화되어 등록됩니다.\n\n"
        "입력 단계 보안: 결제 관련 민감 정보 입력 시에는 AI의 화면 분석 기능을 일시 제한하며, 사용자의 기기 내에서 직접 암호화 처리를 수행하여 정보 유출을 원천 차단합니다.\n\n"
        "데이터 비식별화: 음성 및 이미지 분석을 위해 외부 AI 엔진을 이용할 경우, 개인을 식별할 수 없는 데이터 형태로 가공하여 전송합니다."
    )


__all__ = ["HearbeSignupRule"]
