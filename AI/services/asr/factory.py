"""
ASR Service Factory.

Creates appropriate ASR provider based on configuration.
"""

import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .providers.base import BaseASRProvider

logger = logging.getLogger(__name__)


class ASRProviderType(str, Enum):
    """Available ASR provider types."""
    WHISPER = "whisper"
    QWEN3 = "qwen3"


class ASRServiceFactory:
    """
    Factory for creating ASR service instances.

    Selects the appropriate provider based on config.provider setting.
    """

    @staticmethod
    def create(config) -> "BaseASRProvider":
        """
        Create an ASR provider instance.

        Args:
            config: ASRConfig instance with provider setting

        Returns:
            BaseASRProvider: Configured ASR provider instance

        Raises:
            ValueError: If provider type is unknown
        """
        provider_type = config.provider.lower()

        if provider_type == ASRProviderType.QWEN3:
            from .providers.qwen3 import Qwen3ASRProvider
            logger.info("Creating Qwen3ASRProvider")
            return Qwen3ASRProvider(config)

        elif provider_type == ASRProviderType.WHISPER:
            from .providers.whisper import WhisperASRProvider
            logger.info("Creating WhisperASRProvider")
            return WhisperASRProvider(config)

        else:
            # Default to Whisper for unknown providers
            logger.warning(
                f"Unknown ASR provider '{provider_type}', falling back to Whisper"
            )
            from .providers.whisper import WhisperASRProvider
            return WhisperASRProvider(config)
