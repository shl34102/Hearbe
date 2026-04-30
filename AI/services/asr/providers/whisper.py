"""
Whisper ASR Provider.

Faster-Whisper (turbo) model for speech recognition.
"""

import logging
from typing import Optional

from core.interfaces import ASRResult
from .base import BaseASRProvider

logger = logging.getLogger(__name__)


class WhisperASRProvider(BaseASRProvider):
    """
    Faster-Whisper based ASR provider.

    Features:
    - GPU accelerated transcription
    - Korean language optimized
    - Batch transcription
    """

    async def initialize(self):
        """Load Whisper model."""
        try:
            from faster_whisper import WhisperModel

            logger.info(
                f"Loading Whisper model: {self._config.model_name} "
                f"(device={self._config.device}, compute_type={self._config.compute_type})"
            )
            self._model = WhisperModel(
                self._config.model_name,
                device=self._config.device,
                compute_type=self._config.compute_type
            )
            self._ready = True
            logger.info(f"Whisper model loaded: {self._config.model_name}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    async def transcribe(
        self,
        audio_data: bytes,
        is_final: bool = True,
        segment_id: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe audio to text using Faster-Whisper.

        Args:
            audio_data: Audio bytes (WAV or raw PCM, 16kHz, mono)
            is_final: Whether this is the final transcription for the segment
            segment_id: Optional segment identifier for tracking

        Returns:
            ASRResult: Transcription result
        """
        if not self._ready:
            raise RuntimeError("Whisper model not initialized")

        try:
            audio_array = self._preprocess_audio(audio_data)
            duration = len(audio_array) / 16000.0

            segments, info = self._model.transcribe(
                audio_array,
                language=self._config.language,
                beam_size=self._config.beam_size,
                word_timestamps=False
            )

            # Collect all segment texts
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            text = " ".join(text_parts)
            confidence = info.language_probability if hasattr(info, "language_probability") else 1.0

            logger.debug(f"Whisper transcribed ({duration:.2f}s): {text[:80]}...")
            return ASRResult(
                text=text,
                confidence=confidence,
                language=self._config.language,
                duration=duration,
                is_final=is_final,
                segment_id=segment_id
            )
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise
