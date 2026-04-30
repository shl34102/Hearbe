# -*- coding: utf-8 -*-
"""
HTTP client for backend /product API.

This is used by the AI server to sync extracted product metadata to our backend,
using the same Bearer access token used for /api/orders.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# nginx proxies /api/* to backend
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "https://i14d108.p.ssafy.io/api").rstrip("/")


@dataclass
class ProductCreateRequest:
    name: str
    category_path: List[str]
    coupang_product_number: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": self.name,
            "category_path": self.category_path,
        }
        if self.coupang_product_number:
            payload["coupang_product_number"] = self.coupang_product_number
        return payload


class ProductClient:
    def __init__(self, jwt_token: Optional[str] = None, backend_url: str = DEFAULT_BACKEND_URL):
        self._jwt_token = jwt_token
        self._backend_url = (backend_url or DEFAULT_BACKEND_URL).rstrip("/")

    async def create_product(
        self,
        *,
        name: str,
        category_path: List[str],
        coupang_product_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        token = (self._jwt_token or "").strip()
        if not token:
            return {
                "success": False,
                "error": "JWT token not provided. User needs to login first.",
                "status_code": 401,
            }

        request = ProductCreateRequest(
            name=name,
            category_path=category_path,
            coupang_product_number=coupang_product_number,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._backend_url}/product",
                    json=request.to_dict(),
                    headers=headers,
                )

                if 200 <= response.status_code < 300:
                    data = None
                    try:
                        data = response.json()
                    except Exception:
                        data = {"raw": response.text}
                    logger.info("Product synced successfully: status=%s", response.status_code)
                    return {"success": True, "data": data, "status_code": response.status_code}

                if response.status_code == 401:
                    # Token expired, clear cache for next attempt.
                    self._jwt_token = None
                    return {
                        "success": False,
                        "error": "JWT token expired. User needs to re-login.",
                        "status_code": 401,
                    }

                error_msg = response.text
                logger.warning("Product sync failed: %s - %s", response.status_code, error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                }

        except httpx.RequestError as e:
            logger.error("HTTP request failed: %s", e)
            return {"success": False, "error": str(e)}

