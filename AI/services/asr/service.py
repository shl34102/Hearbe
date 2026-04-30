"""
ASR Service Implementation

Factory-based ASR service that delegates to appropriate provider.
Supports Faster-Whisper and Qwen3-ASR backends via configuration.
"""

import logging
from typing import AsyncGenerator, Optional

from core.interfaces import IASRService, ASRResult
from core.config import get_config
from .factory import ASRServiceFactory

logger = logging.getLogger(__name__)


class ASRService(IASRService):
    """
    ASR Service wrapper that uses factory pattern.

    Delegates to appropriate provider (Whisper or Qwen3) based on config.
    Maintains backward compatibility with existing code.
    """

    def __init__(self):
        """Initialize ASR service with provider from config."""
        config = get_config().asr
        self._provider = ASRServiceFactory.create(config)
        logger.info(f"ASRService initialized with provider: {config.provider}")

    async def initialize(self):
        """Load the ASR model."""
        await self._provider.initialize()

    async def transcribe(
        self,
        audio_data: bytes,
        is_final: bool = True,
        segment_id: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio bytes (WAV or raw PCM, 16kHz, mono)
            is_final: Whether this is the final transcription for the segment
            segment_id: Optional segment identifier for tracking

        Returns:
            ASRResult: Transcription result
        """
        return await self._provider.transcribe(audio_data, is_final, segment_id)

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[ASRResult, None]:
        """
        Stream audio chunks and yield transcription results.

        Args:
            audio_chunks: Async generator of audio bytes

        Yields:
            ASRResult: Intermediate/final transcription results
        """
        async for result in self._provider.transcribe_stream(audio_chunks):
            yield result

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready."""
        return self._provider.is_ready()

    async def shutdown(self):
        """Release resources."""
        await self._provider.shutdown()
        logger.info("ASRService shutdown")
