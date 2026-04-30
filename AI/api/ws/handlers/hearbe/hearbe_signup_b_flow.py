# -*- coding: utf-8 -*-
"""
Hearbe B signup step-by-step flow.
"""

from __future__ import annotations

import re
from typing import Optional

from core.interfaces import MCPCommand
from services.llm.sites.site_manager import get_current_site, get_page_type, get_selector
from .hearbe_signup_flow import CTX_SIGNUP_LAST_ID, CTX_SIGNUP_LAST_PW


CTX_FLOW_ACTIVE = "hearbe_b_signup_flow_active"
CTX_FLOW_STEP = "hearbe_b_signup_flow_step"
CTX_FLOW_URL = "hearbe_b_signup_flow_url"
CTX_FLOW_PW = "hearbe_b_signup_flow_pw"

STEP_ID = "id"
STEP_PASSWORD = "password"
STEP_PASSWORD_CONFIRM = "password_confirm"
STEP_NAME = "name"
STEP_PHONE = "phone"
STEP_TERMS = "terms"
STEP_SUBMIT = "submit"

class HearbeSignupBFlowManager:
    def __init__(self, sender, session_manager):
        self._sender = sender
        self._session = session_manager

    async def handle_page_update(self, session_id: str, url: str) -> bool:
        if not self._sender or not self._session:
            return False
        if not _is_hearbe_b_signup(url):
            if self._session.get_context(session_id, CTX_FLOW_ACTIVE):
                self._clear_flow(session_id)
            return False

        # Start flow on first entry to B signup page.
        if not self._session.get_context(session_id, CTX_FLOW_ACTIVE):
            self._session.set_context(session_id, CTX_FLOW_ACTIVE, True)
            self._session.set_context(session_id, CTX_FLOW_STEP, STEP_ID)
            self._session.set_context(session_id, CTX_FLOW_URL, url)
            await self._sender.send_tts_response(session_id, "아이디를 말씀해주세요.")
            return True

        return False

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        if not self._session or not self._sender:
            return False
        if not self._session.get_context(session_id, CTX_FLOW_ACTIVE):
            return False

        session = self._session.get_session(session_id)
        if not session or not _is_hearbe_b_signup(session.current_url or ""):
            self._clear_flow(session_id)
            return False

        normalized = _normalize_text(text)
        if not normalized:
            return True

        step = self._session.get_context(session_id, CTX_FLOW_STEP) or STEP_ID
        current_url = session.current_url or ""

        if step == STEP_ID:
            username = _extract_username(normalized)
            if not username:
                await self._sender.send_tts_response(session_id, "아이디를 다시 말씀해주세요.")
                return True

            self._session.set_context(session_id, CTX_SIGNUP_LAST_ID, username)
            id_selector = get_selector(current_url, "username_input") or "input[type='text']"
            dup_selector = get_selector(current_url, "username_check_button") or "button:has-text('중복확인')"
            modal_confirm = get_selector(current_url, "modal_confirm") or "button.swal2-confirm"

            commands = [
                MCPCommand(
                    tool_name="wait_for_selector",
                    arguments={"selector": id_selector, "state": "visible", "timeout": 8000},
                    description="아이디 입력 입력칸 대기",
                ),
                MCPCommand(
                    tool_name="fill",
                    arguments={"selector": id_selector, "text": username},
                    description="아이디 입력",
                ),
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": dup_selector},
                    description="아이디 중복확인",
                ),
                MCPCommand(
                    tool_name="wait_for_selector",
                    arguments={"selector": modal_confirm, "state": "visible", "timeout": 4000},
                    description="중복확인 모달 대기",
                ),
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": modal_confirm},
                    description="중복확인 모달 확인",
                ),
            ]
            await self._sender.send_tool_calls(session_id, commands)
            await self._sender.send_tts_response(
                session_id,
                "중복 확인이 완료되었습니다. 사용 가능한 아이디입니다.",
            )
            self._session.set_context(session_id, CTX_FLOW_STEP, STEP_PASSWORD)
            await self._sender.send_tts_response(session_id, "비밀번호를 말씀해주세요.")
            return True

        if step == STEP_PASSWORD:
            password = _extract_password(normalized)
            if not password:
                await self._sender.send_tts_response(session_id, "비밀번호를 다시 말씀해주세요.")
                return True

            self._session.set_context(session_id, CTX_FLOW_PW, password)
            self._session.set_context(session_id, CTX_SIGNUP_LAST_PW, password)
            pw_selector = get_selector(current_url, "password_input") or "input[type='password']"
            commands = [
                MCPCommand(
                    tool_name="wait_for_selector",
                    arguments={"selector": pw_selector, "state": "visible", "timeout": 8000},
                    description="비밀번호 입력 입력칸 대기",
                ),
                MCPCommand(
                    tool_name="fill",
                    arguments={"selector": pw_selector, "text": password},
                    description="비밀번호 입력",
                ),
            ]
            await self._sender.send_tool_calls(session_id, commands)
            self._session.set_context(session_id, CTX_FLOW_STEP, STEP_PASSWORD_CONFIRM)
            await self._sender.send_tts_response(session_id, "비밀번호 확인을 위해 다시 한번 말씀해 주세요.")
            return True

        if step == STEP_PASSWORD_CONFIRM:
            password = _extract_password(normalized)
            if not password:
                await self._sender.send_tts_response(session_id, "비밀번호를 다시 말씀해주세요.")
                return True

            expected = self._session.get_context(session_id, CTX_FLOW_PW)
            if expected and password != expected:
                await self._sender.send_tts_response(session_id, "비밀번호가 일치하지 않습니다. 다시 말씀해주세요.")
                return True

            # B형 가입 화면에는 비밀번호 확인 입력칸이 없으므로
            # 음성 확인만으로 단계 이동한다.
            self._session.set_context(session_id, CTX_FLOW_STEP, STEP_NAME)
            await self._sender.send_tts_response(session_id, "이름을 말씀해주세요.")
            return True

        if step == STEP_NAME:
            name = _extract_name(normalized)
            if not name:
                await self._sender.send_tts_response(session_id, "이름을 다시 말씀해주세요.")
                return True

            name_selector = get_selector(current_url, "name_input") or "input[name='name']"
            commands = [
                MCPCommand(
                    tool_name="wait_for_selector",
                    arguments={"selector": name_selector, "state": "visible", "timeout": 8000},
                    description="이름 입력 입력칸 대기",
                ),
                MCPCommand(
                    tool_name="fill",
                    arguments={"selector": name_selector, "text": name},
                    description="이름 입력",
                ),
            ]
            await self._sender.send_tool_calls(session_id, commands)
            self._session.set_context(session_id, CTX_FLOW_STEP, STEP_PHONE)
            await self._sender.send_tts_response(session_id, "휴대폰 번호를 말씀해주세요.")
            return True

        if step == STEP_PHONE:
            if _is_skip_phone(normalized):
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_TERMS)
                await self._start_terms(session_id)
                return True

            phone = _extract_phone(normalized)
            if not phone:
                await self._sender.send_tts_response(
                    session_id,
                    "휴대폰 번호를 다시 말씀해주세요. 없으면 건너뛴다고 말씀해주세요.",
                )
                return True

            phone_selector = get_selector(current_url, "phone_input") or "input[name='phone']"
            commands = [
                MCPCommand(
                    tool_name="wait_for_selector",
                    arguments={"selector": phone_selector, "state": "visible", "timeout": 8000},
                    description="휴대폰 번호 입력칸 대기",
                ),
                MCPCommand(
                    tool_name="fill",
                    arguments={"selector": phone_selector, "text": phone},
                    description="휴대폰 번호 입력",
                ),
            ]
            await self._sender.send_tool_calls(session_id, commands)
            self._session.set_context(session_id, CTX_FLOW_STEP, STEP_TERMS)
            await self._start_terms(session_id)
            return True

        if step == STEP_TERMS:
            # Terms are read immediately; allow manual skip command to proceed.
            self._session.set_context(session_id, CTX_FLOW_STEP, STEP_SUBMIT)
            await self._submit_signup(session_id, current_url)
            return True

        if step == STEP_SUBMIT:
            await self._submit_signup(session_id, current_url)
            return True

        return False

    async def _start_terms(self, session_id: str) -> None:
        await self._sender.send_tts_response(
            session_id,
            "약관을 읽어드리겠습니다. 중간에 스킵을 원하시면 스페이스바를 눌러주세요.",
        )
        parts = _split_terms_text(_build_terms_text(), parts=2)
        await self._sender.send_tts_response(session_id, parts[0])
        if len(parts) > 1:
            await self._sender.send_tts_response(session_id, parts[1])
        session = self._session.get_session(session_id) if self._session else None
        current_url = session.current_url if session else ""
        if current_url:
            selector = get_selector(current_url, "terms_checkbox") or "input[type='checkbox']"
            commands = [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": selector},
                    description="약관 동의 체크",
                )
            ]
            await self._sender.send_tool_calls(session_id, commands)
        self._session.set_context(session_id, CTX_FLOW_STEP, STEP_SUBMIT)
        await self._submit_signup(session_id, current_url)

    async def _submit_signup(self, session_id: str, current_url: str) -> None:
        submit_selector = get_selector(current_url, "submit_button") or "button:has-text('회원가입')"
        modal_confirm = get_selector(current_url, "modal_confirm") or "button.swal2-confirm"
        commands = [
            MCPCommand(
                tool_name="click",
                arguments={"selector": submit_selector},
                description="회원가입 제출",
            ),
            MCPCommand(
                tool_name="wait",
                arguments={"ms": 1500},
                description="회원가입 처리 대기",
            ),
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": modal_confirm, "state": "visible", "timeout": 4000},
                description="회원가입 완료 모달 대기",
            ),
            MCPCommand(
                tool_name="click",
                arguments={"selector": modal_confirm},
                description="회원가입 완료 확인",
            ),
        ]
        await self._sender.send_tool_calls(session_id, commands)
        await self._sender.send_tts_response(session_id, "회원가입을 진행합니다.")
        self._clear_flow(session_id)

    def _clear_flow(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_FLOW_ACTIVE, None)
        self._session.set_context(session_id, CTX_FLOW_STEP, None)
        self._session.set_context(session_id, CTX_FLOW_URL, None)
        self._session.set_context(session_id, CTX_FLOW_PW, None)

    def cleanup_session(self, session_id: str) -> None:
        self._clear_flow(session_id)


def _is_hearbe_b_signup(url: str) -> bool:
    if not url:
        return False
    if get_page_type(url) != "signup":
        return False
    site = get_current_site(url)
    if not site or getattr(site, "site_id", "") != "hearbe":
        return False
    return "/b/" in url.lower()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _extract_username(text: str) -> Optional[str]:
    value = _extract_labeled_alnum(text, ("아이디", "id"), 4, 20)
    if value:
        return value
    match = re.search(r"[A-Za-z0-9]{4,20}", text)
    return match.group(0) if match else None


def _extract_password(text: str) -> Optional[str]:
    digits = re.sub(r"\D", "", text)
    if len(digits) == 6:
        return digits
    value = _extract_labeled_alnum(text, ("비밀번호", "비번", "패스워드", "password", "pw"), 4, 32)
    if value:
        return value
    if len(digits) >= 4:
        return digits
    return None


def _extract_name(text: str) -> Optional[str]:
    value = _extract_labeled_name(text, ("이름", "성함", "성명", "name"))
    if value:
        return value
    match = re.search(r"[가-힣]{2,4}", text)
    if match:
        return match.group(0)
    return None


def _extract_phone(text: str) -> Optional[str]:
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return None


def _is_skip_phone(text: str) -> bool:
    return any(token in text for token in ("없어", "없습니다", "안할래", "건너", "스킵", "패스", "넘김"))


def _extract_labeled_alnum(text: str, labels: tuple[str, ...], min_len: int, max_len: int) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?:{label_pattern})\s*(?:[:=\-]?\s*)?([A-Za-z0-9\s]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    value = re.sub(r"\s+", "", match.group(1))
    value = re.sub(r"[^A-Za-z0-9]", "", value)
    if len(value) < min_len or len(value) > max_len:
        return None
    return value


def _extract_labeled_name(text: str, labels: tuple[str, ...]) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?:{label_pattern})\s*(?:[:=\-]?\s*)?([가-힣A-Za-z\s]+)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1).strip()
    value = re.sub(r"\s+", " ", value)
    if len(value) < 2:
        return None
    return value


def _build_terms_text() -> str:
    return (
        "제1조 (AI 에이전트 서비스 이용 안내)\n"
        "본 서비스는 사용자의 편리한 쇼핑을 위해 AI 에이전트 기술을 활용합니다.\n\n"
        "AI 브라우저 대리 조작: 사용자가 음성으로 명령하면, HearBe의 AI 에이전트가 가상 브라우저를 통해\n"
        "실제 쇼핑몰 웹사이트를 사용자를 대신하여 탐색하고 조작합니다.\n"
        "이는 사용자가 직접 화면을 보고 클릭하는 과정을 AI가 음성 명령에 따라 수행하는 것입니다.\n\n"
        "화면 분석 및 정보 제공: AI는 쇼핑몰의 이미지와 텍스트를 실시간으로 분석하여 사용자에게 음성으로 전달합니다.\n"
        "이 과정에서 정확한 정보 전달을 위해 화면 캡처 및 텍스트 추출이 이루어질 수 있습니다.\n\n"
        "---------------------------------------------\n\n"
        "제2조 (개인정보 수집 및 이용 항목)\n"
        "서비스 제공을 위해 아래와 같은 정보를 수집합니다. 수집된 정보는 회원 탈퇴 시 또는 법정 보유 기간 종료 시 즉시 파기됩니다.\n\n"
        "1. 시각장애인 사용자 (A형·B형)\n"
        "- 필수 수집 항목: 아이디, 비밀번호, 이름\n"
        "- 선택 수집 항목: 휴대폰 번호\n"
        "- 장애인 복지 카드 확인 정보: 카드사, 카드번호 뒤 4자리, 유효기간 (사용자 맞춤형 UI 제공 목적)\n"
        "- 음성 데이터: 음성 명령 인식 및 처리 (목적 달성 후 즉시 파기)\n\n"
        "2. 일반인 및 보호자 사용자 (C형)\n"
        "- 필수 수집 항목: 아이디, 비밀번호, 이름, 이메일 주소\n"
        "- 원격 제어 정보: 사용자 브라우저 원격 조종을 위한 접속 로그 및 명령 데이터\n\n"
        "---------------------------------------------\n\n"
        "제3조 (결제 보안 및 민감 정보 보호)\n"
        "결제 확인: AI가 사용자를 대신해 결제 단계까지 진입할 수 있으나, 실제 결제 승인은 사용자의 최종 확인이 있어야만 완료됩니다.\n\n"
        "비밀번호 미저장 원칙: 사용자의 결제 비밀번호는 서비스 내 어떠한 장치나 서버에도 저장되지 않으며,\n"
        "결제 시마다 사용자가 직접 입력하는 것을 원칙으로 합니다.\n\n"
        "기기 기반 암호화 등록: 복지 카드 정보 등 서비스 이용을 위해 등록한 민감 정보는 서버에 저장되지 않으며,\n"
        "사용자가 서비스에 접속한 해당 웹 브라우저 및 기기에만 암호화되어 등록됩니다.\n\n"
        "입력 단계 보안: 결제 관련 민감 정보 입력 시에는 AI의 화면 분석 기능을 일시 제한하며,\n"
        "사용자의 기기 내에서 직접 암호화 처리를 수행하여 정보 유출을 원천 차단합니다.\n\n"
        "데이터 비식별화: 음성 및 이미지 분석을 위해 외부 AI 엔진을 이용할 경우,\n"
        "개인을 식별할 수 없는 데이터 형태로 가공하여 전송합니다."
    )


__all__ = ["HearbeSignupBFlowManager"]


def _split_terms_text(text: str, parts: int = 2) -> list[str]:
    if not text:
        return [""]
    if parts <= 1:
        return [text]

    total = len(text)
    target = total // parts
    window = max(200, total // 10)
    start = max(0, target - window)
    end = min(total, target + window)

    split = -1
    for marker in ("\n\n", "\n", "다.", ". "):
        pos = text.find(marker, target, end)
        if pos != -1:
            split = pos + len(marker)
            break
    if split == -1:
        for marker in ("\n\n", "\n", "다.", ". "):
            pos = text.rfind(marker, start, target)
            if pos != -1:
                split = pos + len(marker)
                break
    if split == -1:
        split = target

    first = text[:split].strip()
    second = text[split:].strip()
    if not second:
        return [first]
    return [first, second]
