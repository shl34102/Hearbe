# -*- coding: utf-8 -*-
"""
HTTP client for backend /orders API.

Handles JWT authentication from Chrome profile cookies.
"""

import logging
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# Windows DPAPI for cookie decryption
try:
    import win32crypt
    HAS_WIN32CRYPT = True
except ImportError:
    HAS_WIN32CRYPT = False

# Cryptography for AES decryption (Chrome 80+)
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import base64
    import json
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

logger = logging.getLogger(__name__)

# Backend API configuration
# nginx proxies /api/* to backend
DEFAULT_BACKEND_URL = "https://i14d108.p.ssafy.io/api"
COUPANG_PLATFORM_ID = 1

# Common JWT cookie names to check
JWT_COOKIE_NAMES = ["access_token", "accessToken", "jwt", "token", "Authorization"]


@dataclass
class OrderItem:
    """Single order item matching backend OrderItemDto."""
    name: str
    price: int
    quantity: int = 1
    url: Optional[str] = None
    img_url: Optional[str] = None
    deliver_url: Optional[str] = None
    coupang_product_number: Optional[str] = None
    category_path: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "url": self.url,
            "img_url": self.img_url,
            "deliver_url": self.deliver_url,
        }
        if self.coupang_product_number:
            payload["coupang_product_number"] = self.coupang_product_number
        if self.category_path:
            payload["category_path"] = self.category_path
        return payload


@dataclass
class OrderCreateRequest:
    """Request body for POST /orders matching backend OrderCreateRequest."""
    platform_id: int
    order_url: Optional[str] = None
    items: List[OrderItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "order_url": self.order_url,
            "items": [item.to_dict() for item in self.items],
        }


class ChromeCookieExtractor:
    """Extracts JWT token from Chrome profile cookies."""

    def __init__(self, profile_path: Optional[Path] = None):
        if profile_path:
            self._profile_path = Path(profile_path)
        else:
            # Default: MCP/.mcp_chrome_profile
            project_root = Path(__file__).resolve().parents[3]
            self._profile_path = project_root / "MCP" / ".mcp_chrome_profile"

    def _get_encryption_key(self) -> Optional[bytes]:
        """Get Chrome's encryption key from Local State file."""
        if not HAS_CRYPTOGRAPHY or not HAS_WIN32CRYPT:
            return None

        local_state_path = self._profile_path / "Local State"
        if not local_state_path.exists():
            logger.warning("Local State file not found: %s", local_state_path)
            return None

        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)

            encrypted_key_b64 = local_state.get("os_crypt", {}).get("encrypted_key")
            if not encrypted_key_b64:
                return None

            encrypted_key = base64.b64decode(encrypted_key_b64)
            # Remove "DPAPI" prefix
            encrypted_key = encrypted_key[5:]
            # Decrypt using DPAPI
            key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            return key
        except Exception as e:
            logger.error("Failed to get encryption key: %s", e)
            return None

    def _decrypt_cookie_value(self, encrypted_value: bytes, key: Optional[bytes]) -> Optional[str]:
        """Decrypt Chrome cookie value."""
        if not encrypted_value:
            return None

        # Chrome 80+ uses AES-GCM with "v10" or "v11" prefix
        if encrypted_value[:3] in (b"v10", b"v11"):
            if not key or not HAS_CRYPTOGRAPHY:
                logger.warning("Cannot decrypt v10/v11 cookie without key")
                return None
            try:
                nonce = encrypted_value[3:15]
                ciphertext = encrypted_value[15:]
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(nonce, ciphertext, None)
                return decrypted.decode("utf-8")
            except Exception as e:
                logger.error("AES decryption failed: %s", e)
                return None

        # Older Chrome versions use DPAPI directly
        if HAS_WIN32CRYPT:
            try:
                decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                return decrypted.decode("utf-8")
            except Exception as e:
                logger.error("DPAPI decryption failed: %s", e)
                return None

        return None

    def get_jwt_token(self, domain: str = "i14d108.p.ssafy.io") -> Optional[str]:
        """
        Extract JWT token from Chrome cookies for the specified domain.

        Args:
            domain: Target domain to search for JWT cookie

        Returns:
            JWT token string or None if not found
        """
        cookies_db = self._profile_path / "Default" / "Network" / "Cookies"
        if not cookies_db.exists():
            logger.warning("Cookies database not found: %s", cookies_db)
            return None

        # Copy database to temp file (Chrome may lock it)
        temp_db = None
        try:
            temp_fd, temp_db = tempfile.mkstemp(suffix=".db")
            os.close(temp_fd)
            shutil.copy2(cookies_db, temp_db)

            key = self._get_encryption_key()

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # Query cookies for the domain
            for cookie_name in JWT_COOKIE_NAMES:
                cursor.execute(
                    """
                    SELECT encrypted_value, value
                    FROM cookies
                    WHERE host_key LIKE ? AND name = ?
                    ORDER BY creation_utc DESC
                    LIMIT 1
                    """,
                    (f"%{domain}%", cookie_name),
                )
                row = cursor.fetchone()
                if row:
                    encrypted_value, plain_value = row
                    # Try plain value first
                    if plain_value:
                        logger.info("Found JWT in cookie '%s' (plain)", cookie_name)
                        return plain_value
                    # Try decryption
                    if encrypted_value:
                        decrypted = self._decrypt_cookie_value(encrypted_value, key)
                        if decrypted:
                            logger.info("Found JWT in cookie '%s' (encrypted)", cookie_name)
                            return decrypted

            conn.close()
            logger.warning("No JWT cookie found for domain: %s", domain)
            return None

        except Exception as e:
            logger.error("Failed to extract JWT from cookies: %s", e)
            return None
        finally:
            if temp_db and os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except Exception:
                    pass


class OrderClient:
    """
    HTTP client for backend /orders API.

    Usage:
        client = OrderClient()
        # Auto-extract JWT from Chrome profile
        success = await client.create_order(items=[...])

        # Or provide JWT manually
        client = OrderClient(jwt_token="your_jwt_token")
    """

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        jwt_token: Optional[str] = None,
        chrome_profile_path: Optional[Path] = None,
    ):
        self._backend_url = backend_url.rstrip("/")
        self._jwt_token = jwt_token
        self._cookie_extractor = ChromeCookieExtractor(chrome_profile_path)

    def _get_auth_token(self) -> Optional[str]:
        """Get JWT token from cache or extract from Chrome."""
        if self._jwt_token:
            return self._jwt_token

        # Extract from Chrome cookies
        token = self._cookie_extractor.get_jwt_token()
        if token:
            self._jwt_token = token
        return token

    async def create_order(
        self,
        items: List[OrderItem],
        platform_id: int = COUPANG_PLATFORM_ID,
        order_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create order via backend API.

        Args:
            items: List of OrderItem to create
            platform_id: Platform ID (1 = Coupang)
            order_url: Source order detail page URL

        Returns:
            API response dict with success status and data/error
        """
        token = self._get_auth_token()
        if not token:
            return {
                "success": False,
                "error": "JWT token not found. User needs to login first.",
            }

        request = OrderCreateRequest(platform_id=platform_id, order_url=order_url, items=items)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._backend_url}/orders",
                    json=request.to_dict(),
                    headers=headers,
                )

                if response.status_code == 201:
                    data = response.json()
                    logger.info("Order created successfully: %s", data)
                    return {"success": True, "data": data}
                elif response.status_code == 401:
                    # Token expired, clear cache
                    self._jwt_token = None
                    return {
                        "success": False,
                        "error": "JWT token expired. User needs to re-login.",
                        "status_code": 401,
                    }
                else:
                    error_msg = response.text
                    logger.error("Order creation failed: %s - %s", response.status_code, error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

        except httpx.RequestError as e:
            logger.error("HTTP request failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_my_orders(self) -> Dict[str, Any]:
        """
        Get user's order history from backend.

        Returns:
            API response dict with success status and orders data
        """
        token = self._get_auth_token()
        if not token:
            return {
                "success": False,
                "error": "JWT token not found. User needs to login first.",
            }

        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self._backend_url}/orders/me",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "data": data}
                elif response.status_code == 401:
                    self._jwt_token = None
                    return {
                        "success": False,
                        "error": "JWT token expired. User needs to re-login.",
                        "status_code": 401,
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code,
                    }

        except httpx.RequestError as e:
            logger.error("HTTP request failed: %s", e)
            return {"success": False, "error": str(e)}
