# -*- coding: utf-8 -*-
"""
TTS messages for LLM error handling.

Edit these strings to customize user-facing messages.
"""

CLIENT_ERROR_TTS = {
    "timeout": "응답이 지연되고 있어 다시 시도합니다. 잠시만 기다려 주세요.",
    "network_error": "네트워크 오류로 다시 시도합니다. 잠시만 기다려 주세요.",
    "rate_limit": "요청이 많아 잠시 후 다시 시도합니다.",
    "server_error": "서버가 불안정하여 다시 시도합니다. 잠시만 기다려 주세요.",
    "client_error": "요청을 처리할 수 없습니다. 다시 말씀해 주세요.",
    "auth_error": "인증에 실패했습니다. 설정을 확인해 주세요.",
    "empty_response": "응답을 다시 시도합니다. 잠시만 기다려 주세요.",
}

PARSE_ERROR_TTS = {
    "json_parse": "응답을 다시 확인 중입니다. 잠시만 기다려 주세요.",
    "schema_error": "응답 형식이 맞지 않아 다시 시도합니다. 잠시만 기다려 주세요.",
}

FALLBACK_TTS = "요청을 처리할 수 없습니다. 다시 말씀해 주세요."
