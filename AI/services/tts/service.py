"""
TTS 서비스 구현

Google Cloud TTS Chirp 지원
"""

import os
import logging
from typing import AsyncGenerator, Dict, List, Optional
from core.interfaces import ITTSService, TTSChunk
from core.config import get_config

logger = logging.getLogger(__name__)

# Google Cloud TTS (lazy import)
texttospeech = None


class TTSService(ITTSService):
    """
    TTS 서비스

    Google Cloud TTS Chirp3 HD 사용 (한국어 최적화)
    """

    def __init__(self):
        self._config = get_config().tts
        self._google_client = None

    async def initialize(self):
        """TTS 클라이언트 초기화"""
        try:
            await self._init_google()
            logger.info("TTS service initialized: Google Cloud TTS")
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            raise

    async def _init_google(self):
        """Google Cloud TTS 클라이언트 초기화"""
        global texttospeech

        # Lazy import
        if texttospeech is None:
            from google.cloud import texttospeech as tts_module
            texttospeech = tts_module

        # 인증 설정: config value or env var
        credentials_path = (
            self._config.google_credentials_path
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        )

        if credentials_path:
            # Convert relative path to absolute for Docker compatibility
            if not os.path.isabs(credentials_path):
                credentials_path = os.path.abspath(credentials_path)

            # Verify file exists
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Google credentials file not found: {credentials_path}. "
                    f"CWD: {os.getcwd()}"
                )

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            logger.info(f"Using Google credentials from: {credentials_path}")
        else:
            logger.warning("No Google credentials path configured, using ADC")

        # 클라이언트 초기화
        self._google_client = texttospeech.TextToSpeechClient()
        logger.info(f"Google Cloud TTS initialized with voice: {self._config.google_voice_name}")

    async def synthesize(self, text: str) -> bytes:
        """
        텍스트를 음성으로 변환

        Args:
            text: 변환할 텍스트

        Returns:
            bytes: 오디오 데이터 (PCM 16-bit)
        """
        try:
            return await self._synthesize_google(text)
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise

    async def _synthesize_google(self, text: str) -> bytes:
        """Google Cloud TTS Chirp"""
        if self._google_client is None:
            raise RuntimeError("Google TTS client not initialized")

        # 입력 텍스트 설정
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # 음성 설정 (Chirp 모델)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name=self._config.google_voice_name,
        )

        # 오디오 출력 설정
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=self._config.sample_rate,
            speaking_rate=self._config.speaking_rate,
        )

        # TTS 요청
        response = self._google_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        logger.debug(f"Google TTS synthesized {len(response.audio_content)} bytes")
        return response.audio_content

    async def synthesize_stream(self, text: str) -> AsyncGenerator[TTSChunk, None]:
        """
        텍스트를 스트리밍 음성으로 변환

        Args:
            text: 변환할 텍스트

        Yields:
            TTSChunk: 오디오 청크
        """
        try:
            async for chunk in self._stream_google(text):
                yield chunk
        except Exception as e:
            logger.error(f"TTS streaming failed: {e}")
            raise

    async def _stream_google(self, text: str) -> AsyncGenerator[TTSChunk, None]:
        """
        Google Cloud TTS 스트리밍

        전체 합성 후 청크로 분할하여 전송
        """
        # 전체 오디오 합성
        audio_data = await self._synthesize_google(text)

        # 청크로 분할하여 전송 (4KB 단위)
        chunk_size = 4096

        for i in range(0, len(audio_data), chunk_size):
            chunk_data = audio_data[i:i + chunk_size]
            is_final = i + chunk_size >= len(audio_data)

            yield TTSChunk(
                audio_data=chunk_data,
                is_final=is_final,
                sample_rate=self._config.sample_rate,
                format="pcm"
            )

    def get_voice_list(self) -> List[Dict[str, str]]:
        """
        사용 가능한 음성 목록 반환

        Returns:
            List[Dict]: 음성 정보 목록
        """
        return [
            {"id": "ko-KR-Chirp3-HD-Leda", "name": "Leda (여성, Chirp3 HD)", "language": "ko"},
            {"id": "ko-KR-Chirp3-HD-Aoede", "name": "Aoede (여성, Chirp3 HD)", "language": "ko"},
            {"id": "ko-KR-Chirp3-HD-Puck", "name": "Puck (남성, Chirp3 HD)", "language": "ko"},
            {"id": "ko-KR-Chirp3-HD-Charon", "name": "Charon (남성, Chirp3 HD)", "language": "ko"},
            {"id": "ko-KR-Chirp3-HD-Kore", "name": "Kore (여성, Chirp3 HD)", "language": "ko"},
            {"id": "ko-KR-Chirp3-HD-Fenrir", "name": "Fenrir (남성, Chirp3 HD)", "language": "ko"},
        ]

    async def shutdown(self):
        """리소스 정리"""
        self._google_client = None
        logger.info("TTS service shutdown")
