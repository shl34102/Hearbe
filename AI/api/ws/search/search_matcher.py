# -*- coding: utf-8 -*-
"""
Search result matcher with optional LLM correction.
"""

import asyncio
import difflib
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Any, Iterable, List, Optional

from .search_insights import get_name

DEFAULT_MATCH_THRESHOLD = float(os.getenv("SEARCH_MATCH_THRESHOLD", "0.45"))
DEFAULT_USE_LLM = os.getenv("SEARCH_MATCH_USE_LLM", "true").lower() in ("1", "true", "yes", "y")
DEFAULT_LLM_MODEL = os.getenv("SEARCH_MATCH_LLM_MODEL", "gpt-5-mini")


@dataclass
class MatchResult:
    item: Dict[str, Any]
    score: float
    matched_name: str
    method: str = "heuristic"
    corrected_query: Optional[str] = None


class LLMQueryCorrector:
    """Optional LLM-based query correction."""

    def __init__(self, model: str = DEFAULT_LLM_MODEL):
        self._model = model
        self._client = None
        try:
            from services.llm.generators.llm_generator import resolve_llm_api_key
            self._api_key = resolve_llm_api_key()
        except Exception:
            self._api_key = (
                os.getenv("GMS_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
        self._base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"

    def _get_client(self):
        if not self._api_key:
            return None
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                return None
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    async def correct(self, query: str, candidates: List[str]) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        if not query or not candidates:
            return None

        candidates = candidates[:20]
        system = (
            "You are a query correction engine. "
            "Given a user query and candidate product names, "
            "return the best matching candidate EXACTLY as provided. "
            "If none match, return an empty string. "
            "Respond as JSON: {\"match\": \"...\"}."
        )
        user = json.dumps({"query": query, "candidates": candidates}, ensure_ascii=False)

        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=200,
            )
            content = response.choices[0].message.content or ""
            data = json.loads(content)
            match = (data.get("match") or "").strip()
            return match if match in candidates else None
        except Exception:
            return None


class SearchMatcher:
    """Match user query to search result items with thresholding."""

    def __init__(
        self,
        threshold: float = DEFAULT_MATCH_THRESHOLD,
        use_llm_correction: bool = DEFAULT_USE_LLM,
    ):
        self._threshold = threshold
        self._use_llm = use_llm_correction
        self._llm_corrector = LLMQueryCorrector() if use_llm_correction else None

    async def match(self, query: str, items: List[Dict[str, Any]]) -> Optional[MatchResult]:
        if not query or not items:
            return None

        result = self._match_heuristic(query, items)
        if result and result.score >= self._threshold:
            return result

        if self._use_llm and self._llm_corrector:
            candidates = [get_name(item) for item in items if get_name(item)]
            corrected = await self._llm_corrector.correct(query, candidates)
            if corrected:
                corrected_result = self._match_heuristic(corrected, items)
                if corrected_result and corrected_result.score >= self._threshold:
                    corrected_result.method = "llm"
                    corrected_result.corrected_query = corrected
                    return corrected_result

        return None

    def _match_heuristic(self, query: str, items: List[Dict[str, Any]]) -> Optional[MatchResult]:
        query_norm = _normalize_match_text(query)
        query_tokens = set(_tokenize(query_norm))
        if not query_norm or not query_tokens:
            return None

        best_item = None
        best_score = 0.0
        best_name = ""
        for item in items:
            name = get_name(item)
            name_norm = _normalize_match_text(name)
            if not name_norm:
                continue
            if query_norm in name_norm or name_norm in query_norm:
                return MatchResult(item=item, score=1.0, matched_name=name, method="substring")

            name_tokens = set(_tokenize(name_norm))
            if not name_tokens:
                continue
            token_overlap = len(query_tokens & name_tokens) / max(len(query_tokens), 1)
            seq_ratio = difflib.SequenceMatcher(None, query_norm, name_norm).ratio()
            score = max(token_overlap, seq_ratio)

            # small boost for partial overlaps
            for token in name_tokens:
                if token and token in query_norm:
                    score += 0.05
            for token in query_tokens:
                if token and token in name_norm:
                    score += 0.05
            score = min(score, 1.0)

            if score > best_score:
                best_score = score
                best_item = item
                best_name = name

        if not best_item:
            return None
        return MatchResult(item=best_item, score=best_score, matched_name=best_name, method="heuristic")


def _normalize_match_text(text: str) -> str:
    if not text:
        return ""
    value = str(text).lower()
    value = value.replace("리터", "l")
    value = re.sub(r"[^0-9a-z가-힣]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"\d+[a-z]+|\d+|[a-z]+|[가-힣]+", text)
