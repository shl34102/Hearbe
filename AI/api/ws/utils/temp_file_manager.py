# -*- coding: utf-8 -*-
"""
Temporary file manager for session-based file storage.

Manages temporary JSON files that are automatically cleaned up when sessions end.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TempFileManager:
    """
    Manages temporary files tied to session lifecycle.

    Files are stored in temp/ directory and automatically deleted when
    the associated session ends.
    """

    def __init__(self, base_dir: str = "temp"):
        """
        Initialize file manager.

        Args:
            base_dir: Base directory for temporary files (default: "temp")
        """
        self.base_dir = Path(base_dir)
        self._session_files: Dict[str, Path] = {}

    def save_json(
        self,
        data: Any,
        session_id: str,
        category: str = "general",
        filename_prefix: str = "data"
    ) -> Optional[Path]:
        """
        Save data to a JSON file for a session.

        Args:
            data: Data to save (must be JSON serializable)
            session_id: Session ID to associate with this file
            category: Subdirectory category (e.g., "search_results", "ocr_results")
            filename_prefix: Prefix for the filename

        Returns:
            Path to saved file, or None if save failed
        """
        try:
            # Delete previous file for this session if exists
            self._delete_previous_file(session_id)

            # Create category directory
            category_dir = self.base_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_short = session_id[:8] if len(session_id) >= 8 else session_id
            filename = f"{filename_prefix}_{timestamp}_{session_short}.json"
            filepath = category_dir / filename

            # Save to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Track file for cleanup
            self._session_files[session_id] = filepath

            logger.info(f"Saved temp file: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save temp file for session {session_id}: {e}")
            return None

    def _delete_previous_file(self, session_id: str) -> bool:
        """
        Delete previous file for a session if it exists.

        Args:
            session_id: Session ID

        Returns:
            True if file was deleted, False otherwise
        """
        if session_id not in self._session_files:
            return False

        old_file = self._session_files[session_id]
        try:
            if old_file.exists():
                old_file.unlink()
                logger.debug(f"Deleted old temp file: {old_file}")
                return True
        except Exception as e:
            logger.warning(f"Failed to delete old temp file {old_file}: {e}")

        return False

    def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up all files associated with a session.

        Args:
            session_id: Session ID to clean up

        Returns:
            True if cleanup was successful, False otherwise
        """
        if session_id not in self._session_files:
            return False

        filepath = self._session_files.pop(session_id)
        try:
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted temp file for session {session_id}: {filepath}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete temp file {filepath}: {e}")

        return False

    def get_filepath(self, session_id: str) -> Optional[Path]:
        """
        Get the current file path for a session.

        Args:
            session_id: Session ID

        Returns:
            Path to the file, or None if no file exists for this session
        """
        return self._session_files.get(session_id)

    def cleanup_all(self):
        """
        Clean up all tracked files and any leftover temp files (e.g., on server shutdown).
        """
        session_ids = list(self._session_files.keys())
        for session_id in session_ids:
            self.cleanup_session(session_id)

        try:
            if not self.base_dir.exists() or not self.base_dir.is_dir():
                return

            for path in self.base_dir.rglob("*"):
                if path.is_file():
                    try:
                        path.unlink()
                        logger.info(f"Deleted temp file: {path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {path}: {e}")

            # Remove empty dirs (bottom-up)
            for path in sorted(self.base_dir.rglob("*"), reverse=True):
                if path.is_dir():
                    try:
                        path.rmdir()
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Temp cleanup failed: {e}")
