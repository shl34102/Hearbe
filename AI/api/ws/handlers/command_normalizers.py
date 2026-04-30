# -*- coding: utf-8 -*-
"""
Command normalization helpers.
"""

import re
from urllib.parse import urlparse

from services.llm.sites.site_manager import get_selector


OTP_FRAME_PATH = "/login/otpLogin.pang"


def _build_otp_frame_url(current_url: str) -> str:
    try:
        parsed = urlparse(current_url or "")
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}{OTP_FRAME_PATH}"
    except Exception:
        pass
    return f"https://login.coupang.com{OTP_FRAME_PATH}"


def _ensure_frame_url(args: dict, frame_url: str) -> None:
    if not args:
        return
    if args.get("frame_url") or args.get("frame_name") or args.get("frame_selector") is not None or args.get("frame_index") is not None:
        return
    args["frame_url"] = frame_url


def _is_otp_selector(selector: str, otp_selector: str | None, otp_submit_selector: str | None) -> bool:
    if not selector:
        return False
    if otp_selector and selector == otp_selector:
        return True
    if otp_submit_selector and selector == otp_submit_selector:
        return True
    tokens = ("smsCode", "loginWithSmsCode", "sendAgain", "sms-login-keep-state", "verify-number", "one-time-code", "otp")
    return any(token in selector for token in tokens)


def normalize_login_phone_commands(commands, current_url: str):
    if not commands:
        return commands
    if "login" not in (current_url or ""):
        return commands

    phone_selector = get_selector(current_url, "phone_input") if current_url else None
    otp_selector = get_selector(current_url, "otp_input") if current_url else None
    otp_submit_selector = get_selector(current_url, "otp_submit_button") if current_url else None
    normalized = []
    otp_frame_url = _build_otp_frame_url(current_url)
    for cmd in commands:
        try:
            tool = cmd.tool_name
            args = cmd.arguments or {}
            selector = args.get("selector", "")
            if tool in ("fill", "fill_input"):
                text = args.get("text") if tool == "fill" else args.get("value")
                if isinstance(text, str):
                    digits = re.sub(r"\D", "", text)
                    if digits:
                        is_phone = len(digits) in (10, 11) and (
                            (phone_selector and selector == phone_selector)
                            or ("_phoneInput" in selector or "phone" in selector or "휴대폰" in selector)
                        )
                        is_otp = len(digits) in (4, 5, 6, 7, 8) and (
                            (otp_selector and selector == otp_selector)
                            or ("one-time-code" in selector or "otp" in selector or "smsCode" in selector)
                        )
                        if is_phone or is_otp:
                            if tool == "fill":
                                args["text"] = digits
                            else:
                                args["value"] = digits
                        if is_otp or _is_otp_selector(selector, otp_selector, otp_submit_selector):
                            _ensure_frame_url(args, otp_frame_url)
                        if is_phone or is_otp:
                            cmd.arguments = args
            if tool in ("click", "click_element"):
                selector = args.get("selector")
                if selector in ("#loginWithSmsCode", "button#loginWithSmsCode") and otp_submit_selector:
                    args["selector"] = otp_submit_selector
                if _is_otp_selector(args.get("selector", ""), otp_selector, otp_submit_selector):
                    _ensure_frame_url(args, otp_frame_url)
                    cmd.arguments = args
            normalized.append(cmd)
        except Exception:
            normalized.append(cmd)
    return normalized
