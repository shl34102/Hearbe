"""
Browser state helpers (login status, etc.).
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BrowserStateMixin:
    """State inspection helpers."""

    async def check_login_status(self) -> Dict[str, Any]:
        """
        Check login status by detecting login/signup or logout UI.

        Returns:
            {"success": bool, "logged_in": bool|None, "login_link": bool, "signup_link": bool, "logout_link": bool}
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        script = """
          () => {
            const isVisible = (el) => {
              if (!el) return false;
              const rect = el.getBoundingClientRect();
              if (!rect || rect.width === 0 || rect.height === 0) return false;
              const style = window.getComputedStyle(el);
              if (!style) return false;
              if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
              return true;
            };

            const loginLink = document.querySelector(
              'a[title="로그인"], a[href*="login.coupang.com"], a[href*="login.pang"], a[href*="/login"]'
            );
            const signupLink = document.querySelector(
              'a[title="회원가입"], a[href*="memberJoin"], a[href*="/signup"], a[href*="/join"]'
            );

            let logoutLink = null;
            const candidates = Array.from(document.querySelectorAll("a, button"));
            for (const el of candidates) {
              const text = (el.innerText || el.textContent || "").trim();
              if (!text) continue;
              if (text.includes("로그아웃") || /logout/i.test(text)) {
                logoutLink = el;
                break;
              }
            }

            const loginVisible = isVisible(loginLink);
            const signupVisible = isVisible(signupLink);
            const logoutVisible = isVisible(logoutLink);

            let loggedIn = null;
            if (logoutVisible) {
              loggedIn = true;
            } else if (loginVisible || signupVisible) {
              loggedIn = false;
            }

            return {
              logged_in: loggedIn,
              login_link: loginVisible,
              signup_link: signupVisible,
              logout_link: logoutVisible
            };
          }
        """

        try:
            result = await page.evaluate(script)
            if isinstance(result, dict):
                return {"success": True, **result}
            return {"success": True, "logged_in": None}
        except Exception as e:
            logger.error(f"Login status check failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_session(self) -> Dict[str, Any]:
        """
        Get user session info from localStorage.

        Returns:
            {"success": bool, "logged_in": bool, "user_type": str|None, "user_id": str|None, ...}
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        script = """
          () => {
            const accessToken = localStorage.getItem('accessToken');
            const refreshToken = localStorage.getItem('refreshToken') || localStorage.getItem('refresh_token');
            const userType = localStorage.getItem('userType');
            const userId = localStorage.getItem('user_id');
            const username = localStorage.getItem('username');
            const userName = localStorage.getItem('user_name');

            return {
              logged_in: !!accessToken,
              access_token: accessToken,
              refresh_token: refreshToken,
              user_type: userType,
              user_id: userId,
              username: username,
              user_name: userName
            };
          }
        """

        try:
            result = await page.evaluate(script)
            if isinstance(result, dict):
                access_token = result.get("access_token")
                refresh_token = result.get("refresh_token")
                logger.info(
                    "get_user_session result: logged_in=%s access_token=%s refresh_token=%s user_type=%s user_id=%s",
                    result.get("logged_in"),
                    "present" if access_token else "missing",
                    "present" if refresh_token else "missing",
                    result.get("user_type") or "missing",
                    result.get("user_id") or "missing",
                )
                return {"success": True, **result}
            return {"success": True, "logged_in": False}
        except Exception as e:
            logger.error(f"Get user session failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_type(self) -> Dict[str, Any]:
        """
        Get user type from localStorage.

        Returns:
            {"success": bool, "user_type": str|None, "path_prefix": str}
            path_prefix: "A" for BLIND, "B" for LOW_VISION, "C" for GENERAL
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        script = """
          () => {
            const userType = localStorage.getItem('userType');
            let pathPrefix = null;
            if (userType === 'BLIND') pathPrefix = 'A';
            else if (userType === 'LOW_VISION') pathPrefix = 'B';
            else if (userType === 'GENERAL') pathPrefix = 'C';

            return {
              user_type: userType,
              path_prefix: pathPrefix
            };
          }
        """

        try:
            result = await page.evaluate(script)
            if isinstance(result, dict):
                return {"success": True, **result}
            return {"success": True, "user_type": None, "path_prefix": None}
        except Exception as e:
            logger.error(f"Get user type failed: {e}")
            return {"success": False, "error": str(e)}
