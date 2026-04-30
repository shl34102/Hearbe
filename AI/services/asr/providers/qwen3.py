"""
Qwen3 ASR Provider.

Qwen3-ASR model for speech recognition with superior Korean support.
"""

import logging
import os
from typing import Optional, Tuple

import numpy as np

from core.interfaces import ASRResult
from .base import BaseASRProvider

logger = logging.getLogger(__name__)


class Qwen3ASRProvider(BaseASRProvider):
    """
    Qwen3-ASR based ASR provider.

    Features:
    - Superior Korean language recognition
    - Multilingual support (30 languages)
    - GPU accelerated with bfloat16
    """

    # Language code mapping: ISO 639-1 -> Qwen3 language name
    LANGUAGE_MAP = {
        "ko": "Korean",
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "ar": "Arabic",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "pt": "Portuguese",
        "id": "Indonesian",
        "it": "Italian",
        "ru": "Russian",
        "th": "Thai",
        "vi": "Vietnamese",
        "tr": "Turkish",
        "hi": "Hindi",
        "ms": "Malay",
        "nl": "Dutch",
        "sv": "Swedish",
        "da": "Danish",
        "fi": "Finnish",
        "pl": "Polish",
        "cs": "Czech",
        "el": "Greek",
        "ro": "Romanian",
        "hu": "Hungarian",
    }

    async def initialize(self):
        """Load Qwen3-ASR model."""
        try:
            import torch
            from qwen_asr import Qwen3ASRModel

            model_name = self._config.qwen3_model_name
            device = self._config.device

            logger.info(
                f"Loading Qwen3-ASR model: {model_name} "
                f"(device={device})"
            )

            offline_env = _env_flag("HF_HUB_OFFLINE") or _env_flag("TRANSFORMERS_OFFLINE")
            local_only_env = _env_flag("QWEN3_LOCAL_ONLY")
            local_files_only = bool(offline_env or local_only_env)

            if local_files_only:
                logger.info("Qwen3-ASR loading in local_files_only mode")

            self._model = Qwen3ASRModel.from_pretrained(
                model_name,
                dtype=torch.bfloat16,
                device_map=device,
                max_inference_batch_size=self._config.qwen3_max_batch_size,
                max_new_tokens=self._config.qwen3_max_new_tokens,
                local_files_only=local_files_only,
            )

            self._ready = True
            logger.info(f"Qwen3-ASR model loaded: {model_name}")

        except Exception as e:
            logger.error(f"Failed to load Qwen3-ASR model: {e}")
            raise

    def _preprocess_audio_tuple(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """
        Convert raw audio bytes to (numpy array, sample_rate) tuple.

        Qwen3-ASR accepts (waveform, sample_rate) tuples.

        Args:
            audio_data: Raw audio bytes

        Returns:
            Tuple[np.ndarray, int]: (audio_array, sample_rate)
        """
        audio_array = self._preprocess_audio(audio_data)
        return (audio_array, 16000)

    def _map_language(self, language_code: str) -> Optional[str]:
        """
        Map ISO 639-1 language code to Qwen3 language name.

        Args:
            language_code: ISO 639-1 code (e.g., "ko", "en")

        Returns:
            str or None: Qwen3 language name, or None for auto-detection
        """
        return self.LANGUAGE_MAP.get(language_code)

    async def transcribe(
        self,
        audio_data: bytes,
        is_final: bool = True,
        segment_id: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe audio to text using Qwen3-ASR.

        Args:
            audio_data: Audio bytes (WAV or raw PCM, 16kHz, mono)
            is_final: Whether this is the final transcription for the segment
            segment_id: Optional segment identifier for tracking

        Returns:
            ASRResult: Transcription result
        """
        if not self._ready:
            raise RuntimeError("Qwen3-ASR model not initialized")

        try:
            audio_tuple = self._preprocess_audio_tuple(audio_data)
            duration = len(audio_tuple[0]) / 16000.0

            # Map language code to Qwen3 format
            language = self._map_language(self._config.language)

            # Transcribe
            results = self._model.transcribe(
                audio=audio_tuple,
                language=language,
                return_time_stamps=False,
            )

            # Extract result
            result = results[0]
            text = result.text.strip() if result.text else ""

            # Qwen3 doesn't provide confidence score, use 1.0
            confidence = 1.0

            # Use detected language or configured language
            detected_language = self._config.language
            if hasattr(result, 'language') and result.language:
                # Map back from Qwen3 language name to ISO code if needed
                detected_language = self._config.language

            logger.debug(f"Qwen3 transcribed ({duration:.2f}s): {text[:80]}...")
            return ASRResult(
                text=text,
                confidence=confidence,
                language=detected_language,
                duration=duration,
                is_final=is_final,
                segment_id=segment_id
            )

        except Exception as e:
            logger.error(f"Qwen3 transcription failed: {e}")
            raise


def _env_flag(name: str) -> bool:
    value = os.getenv(name)
    if not value:
        return False
    return value.strip().lower() in ("1", "true", "yes", "y", "on")
