# -*- coding: utf-8 -*-
"""
LLM client wrapper.

Handles API calls, retries, and logging.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from services.llm.errors.llm_errors import LLMClientError

from .llm_logging import log_llm_request, log_llm_response

logger = logging.getLogger(__name__)


def resolve_llm_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """
    Resolve LLM API key based on environment configuration.

    Order:
    1) explicit_key (if provided)
    2) LLM_API_KEY_NAME -> env value
    3) GMS_API_KEY, OPENAI_API_KEY
    """
    if explicit_key:
        return explicit_key
    key_name = os.environ.get("LLM_API_KEY_NAME")
    if key_name:
        key_value = os.environ.get(key_name)
        if key_value:
            return key_value
    return (
        os.environ.get("GMS_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


class LLMClient:
    """OpenAI client wrapper with retry + logging."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str,
        model: str,
        max_tokens: int,
        timeout_seconds: Optional[float] = None,
    ):
        self.api_key = resolve_llm_api_key(api_key)
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        if timeout_seconds is not None:
            self.timeout_seconds = float(timeout_seconds)
        else:
            try:
                self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", "20"))
            except ValueError:
                self.timeout_seconds = 20.0
        self._client = None

    @property
    def client(self):
        """OpenAI client lazy loading."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                logger.error("openai 패키지가 설치되지 않았습니다: pip install openai")
                raise
        return self._client

    async def request(
        self,
        messages: List[Dict[str, str]],
        current_url: str = "",
        text_len: Optional[int] = None,
        label: str = "",
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        if label:
            logger.info(
                "LLM request (%s): model=%s, msg_count=%d, url=%s",
                label,
                self.model,
                len(messages or []),
                current_url or "(empty)"
            )
        elif text_len is not None:
            logger.info(
                "LLM request: model=%s, text_len=%d, url=%s",
                self.model,
                text_len,
                current_url or "(empty)"
            )
        else:
            logger.info(
                "LLM request: model=%s, msg_count=%d, url=%s",
                self.model,
                len(messages or []),
                current_url or "(empty)"
            )

        token_param = "max_completion_tokens"
        token_limit = max_tokens if max_tokens is not None else self.max_tokens
        log_llm_request(
            logger,
            model=self.model,
            base_url=self.base_url,
            messages=messages,
            max_tokens=token_limit,
            response_format=response_format,
            token_param=token_param,
        )

        content = None
        last_error = None
        for attempt in range(3):
            try:
                create_args = {
                    "model": self.model,
                    "messages": messages,
                    "max_completion_tokens": token_limit,
                }
                if response_format:
                    create_args["response_format"] = response_format
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.chat.completions.create,
                        **create_args,
                    ),
                    timeout=self.timeout_seconds,
                )
                content = response.choices[0].message.content
                logger.info("LLM response received: chars=%d", len(content or ""))
                log_llm_response(logger, response, content)
                if content:
                    break
                last_error = "empty_response"
                if attempt < 2:
                    logger.warning("Empty LLM response received, retrying (%d/2)", attempt + 1)
            except asyncio.TimeoutError as e:
                raise LLMClientError("timeout", "LLM request timed out", e)
            except Exception as e:
                status = getattr(e, "status_code", None) or getattr(e, "status", None)
                if status == 401 or status == 403:
                    raise LLMClientError("auth_error", "LLM auth error", e)
                if status == 429:
                    raise LLMClientError("rate_limit", "LLM rate limit", e)
                if status and 500 <= int(status) <= 599:
                    raise LLMClientError("server_error", "LLM server error", e)
                if status and 400 <= int(status) <= 499:
                    raise LLMClientError("client_error", "LLM client error", e)
                raise LLMClientError("network_error", "LLM network error", e)

        if not content:
            raise LLMClientError("empty_response", last_error or "empty_response")

        return content
