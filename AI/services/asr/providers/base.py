"""
Base ASR Provider abstract class.

All ASR providers must inherit from this class.
"""

import io
import logging
from abc import abstractmethod
from typing import AsyncGenerator, Optional

import numpy as np
import soundfile as sf

from core.interfaces import IASRService, ASRResult

logger = logging.getLogger(__name__)


class BaseASRProvider(IASRService):
    """
    Abstract base class for ASR providers.

    Provides common audio preprocessing logic and defines
    the interface that all providers must implement.
    """

    def __init__(self, config):
        """
        Initialize the provider.

        Args:
            config: ASRConfig instance
        """
        self._config = config
        self._model = None
        self._ready = False

    @abstractmethod
    async def initialize(self):
        """
        Load the ASR model.

        Must set self._ready = True after successful initialization.
        """
        pass

    @abstractmethod
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
        pass

    def _preprocess_audio(self, audio_data: bytes) -> np.ndarray:
        """
        Convert raw audio bytes to numpy array.

        Expects WAV format or raw PCM (16kHz, mono, 16-bit).
        Returns float32 numpy array normalized to [-1, 1].

        Args:
            audio_data: Raw audio bytes

        Returns:
            np.ndarray: Float32 audio array
        """
        try:
            # Try reading as WAV file
            audio_io = io.BytesIO(audio_data)
            audio_array, sample_rate = sf.read(audio_io, dtype="float32")

            # Convert stereo to mono if needed
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)

            # Resample to 16kHz if needed
            if sample_rate != 16000:
                import scipy.signal as signal
                num_samples = int(len(audio_array) * 16000 / sample_rate)
                audio_array = signal.resample(audio_array, num_samples)

            return audio_array.astype(np.float32)

        except Exception:
            # Fallback: assume raw PCM (16-bit, 16kHz, mono)
            logger.debug("WAV parsing failed, treating as raw PCM")
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            return audio_array.astype(np.float32) / 32768.0

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[ASRResult, None]:
        """
        Stream audio chunks and yield transcription results.

        Default implementation buffers chunks and transcribes periodically.

        Args:
            audio_chunks: Async generator of audio bytes

        Yields:
            ASRResult: Intermediate/final transcription results
        """
        if not self._ready:
            raise RuntimeError("ASR model not initialized")

        # Threshold: 1 second of audio (16kHz, 16-bit = 32000 bytes)
        CHUNK_THRESHOLD = 32000

        buffer = b""
        segment_counter = 0

        async for chunk in audio_chunks:
            buffer += chunk

            if len(buffer) >= CHUNK_THRESHOLD:
                segment_counter += 1
                result = await self.transcribe(
                    buffer,
                    is_final=False,
                    segment_id=f"seg_{segment_counter}"
                )
                yield result
                buffer = b""

        # Process remaining buffer as final
        if buffer:
            segment_counter += 1
            result = await self.transcribe(
                buffer,
                is_final=True,
                segment_id=f"seg_{segment_counter}"
            )
            yield result

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready."""
        return self._ready

    async def shutdown(self):
        """Release resources."""
        self._model = None
        self._ready = False
        logger.info(f"{self.__class__.__name__} shutdown")
