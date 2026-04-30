"""
Chrome utility helpers for CDP-based automation.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, Optional


DEFAULT_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
]


def find_chrome_path(configured_path: Optional[str] = None) -> Optional[str]:
    if configured_path:
        path = Path(configured_path)
        if path.exists():
            return str(path)

    env_path = os.getenv("CHROME_PATH") or os.getenv("BROWSER_EXECUTABLE_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return str(path)

    chrome_in_path = shutil.which("chrome") or shutil.which("chrome.exe")
    if chrome_in_path:
        return chrome_in_path

    for path in DEFAULT_CHROME_PATHS:
        path = Path(path)
        if path.exists():
            return str(path)

    return None


def get_env_value(env_path: Path, key: str) -> Optional[str]:
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(f"{key}="):
            return stripped.split("=", 1)[1]

    return None


def has_env_key(env_path: Path, key: str) -> bool:
    if not env_path.exists():
        return False

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(f"{key}="):
            return True

    return False


def update_env_file(env_path: Path, updates: Dict[str, str]) -> bool:
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)

    updated = {key: False for key in updates}

    def has_key(line: str, key: str) -> bool:
        stripped = line.lstrip()
        return not stripped.startswith("#") and stripped.startswith(f"{key}=")

    new_lines = []
    for line in lines:
        replaced = False
        for key, value in updates.items():
            if has_key(line, key):
                new_lines.append(f"{key}={value}\n")
                updated[key] = True
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    for key, value in updates.items():
        if not updated[key]:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] = f"{new_lines[-1]}\n"
            new_lines.append(f"{key}={value}\n")

    env_path.write_text("".join(new_lines), encoding="utf-8")
    return True


def ensure_chrome_env(env_path: Path) -> Optional[str]:
    existing = get_env_value(env_path, "CHROME_PATH")
    if existing:
        path = Path(existing)
        if path.exists():
            return existing

    chrome_path = find_chrome_path()
    if not chrome_path:
        return None

    updates = {"CHROME_PATH": chrome_path}
    if has_env_key(env_path, "BROWSER_EXECUTABLE_PATH"):
        updates["BROWSER_EXECUTABLE_PATH"] = chrome_path
    update_env_file(env_path, updates)
    return chrome_path
