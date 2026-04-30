# -*- coding: utf-8 -*-
"""
OCR Integrator

상세 이미지 URL을 청크 단위로 OCR 처리하고 TTS용 요약을 생성합니다.
WebSocket 스트리밍을 위해 비동기 제너레이터로 결과를 반환합니다.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from core.korean_product_terms import format_product_terms_for_tts
# OCR 파이프라인 경로 추가
OCR_PATH = Path(__file__).parent.parent / "ocr" / "text_processors"
if str(OCR_PATH) not in sys.path:
    sys.path.insert(0, str(OCR_PATH))

logger = logging.getLogger(__name__)


@dataclass
class OCRChunkResult:
    """OCR 청크 처리 결과"""
    chunk_index: int
    total_chunks: int
    image_urls: List[str]
    summary: List[str]
    keywords: Dict[str, Dict]
    product_type: str = "기타"
    is_final: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "image_urls": self.image_urls,
            "summary": self.summary,
            "keywords": self.keywords,
            "product_type": self.product_type,
            "is_final": self.is_final,
            "error": self.error,
        }

    def format_for_tts(self) -> str:
        """TTS용 텍스트로 변환"""
        if self.error:
            return f"이미지 분석 중 오류가 발생했습니다: {self.error}"

        if not self.summary:
            return "이미지에서 추가 정보를 찾지 못했습니다."

        formatted = [format_product_terms_for_tts(line) for line in self.summary if line]
        # 요약 문장들을 연결
        return ". ".join(formatted) + "."


class OCRIntegrator:
    """
    OCR 파이프라인 통합 클래스

    이미지 URL을 청크 단위로 처리하고 비동기로 결과를 반환합니다.
    """

    def __init__(
        self,
        chunk_size: int = 3,
        output_dir: str = "output",
        max_workers: int = 4
    ):
        self.chunk_size = chunk_size
        self.output_dir = output_dir
        self.max_workers = max_workers
        self._ocr_pipeline = None
        self._lock = asyncio.Lock()

    async def warmup(self):
        """서버 시작 시 OCR 파이프라인 및 모델을 미리 로드"""
        logger.info("OCR warmup: loading pipeline and model...")
        pipeline = self._get_pipeline()
        if pipeline is None:
            logger.warning("OCR warmup: pipeline import failed")
            return

        loop = asyncio.get_event_loop()
        try:
            from services.ocr.text_processors.korean_ocr import get_ocr_instance
            await loop.run_in_executor(None, get_ocr_instance)
            logger.info("OCR warmup: model loaded successfully")
        except Exception as e:
            logger.warning(f"OCR warmup: model load failed: {e}")

    def _get_pipeline(self):
        """OCR 파이프라인 레이지 로딩"""
        if self._ocr_pipeline is None:
            try:
                from ocr_pipeline import process_product_from_urls
                self._ocr_pipeline = process_product_from_urls
                logger.info("OCR 파이프라인 로드 완료")
            except ImportError as e:
                logger.error(f"OCR 파이프라인 로드 실패: {e}")
                self._ocr_pipeline = None
        return self._ocr_pipeline

    def _chunk_urls(self, urls: List[str]) -> List[List[str]]:
        """URL 리스트를 청크로 분할"""
        return [
            urls[i:i + self.chunk_size]
            for i in range(0, len(urls), self.chunk_size)
        ]

    async def process_images_chunked(
        self,
        image_urls: List[str],
        site: str = "auto"
    ) -> AsyncGenerator[OCRChunkResult, None]:
        """
        이미지 URL을 청크 단위로 OCR 처리

        Args:
            image_urls: 상세 이미지 URL 리스트
            site: 사이트 (auto/coupang/naver)

        Yields:
            OCRChunkResult: 각 청크의 처리 결과
        """
        if not image_urls:
            yield OCRChunkResult(
                chunk_index=0,
                total_chunks=0,
                image_urls=[],
                summary=["처리할 이미지가 없습니다."],
                keywords={},
                is_final=True
            )
            return

        chunks = self._chunk_urls(image_urls)
        total_chunks = len(chunks)

        logger.info(f"OCR 청크 처리 시작: {len(image_urls)}개 이미지 → {total_chunks}개 청크")

        for idx, chunk_urls in enumerate(chunks):
            is_final = (idx == total_chunks - 1)

            try:
                result = await self._process_chunk(chunk_urls, site, idx)
                result.chunk_index = idx
                result.total_chunks = total_chunks
                result.is_final = is_final
                yield result

            except Exception as e:
                logger.error(f"청크 {idx} 처리 실패: {e}")
                yield OCRChunkResult(
                    chunk_index=idx,
                    total_chunks=total_chunks,
                    image_urls=chunk_urls,
                    summary=[],
                    keywords={},
                    is_final=is_final,
                    error=str(e)
                )

    async def _process_chunk(
        self,
        urls: List[str],
        site: str,
        chunk_index: int
    ) -> OCRChunkResult:
        """단일 청크 처리"""
        pipeline = self._get_pipeline()

        if pipeline is None:
            return OCRChunkResult(
                chunk_index=chunk_index,
                total_chunks=0,
                image_urls=urls,
                summary=[],
                keywords={},
                error="OCR 파이프라인을 로드할 수 없습니다."
            )

        # 동기 OCR 처리를 비동기로 실행
        loop = asyncio.get_event_loop()

        async with self._lock:
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: pipeline(
                        image_urls=urls,
                        site=site,
                        output_dir=self.output_dir,
                        max_workers=self.max_workers,
                        save_result=False,
                        verbose=False
                    )
                )

                return OCRChunkResult(
                    chunk_index=chunk_index,
                    total_chunks=0,
                    image_urls=urls,
                    summary=result.get("summary", []),
                    keywords=result.get("keywords", {}),
                    product_type=result.get("product_type", "기타")
                )

            except Exception as e:
                logger.error(f"OCR 처리 오류: {e}")
                return OCRChunkResult(
                    chunk_index=chunk_index,
                    total_chunks=0,
                    image_urls=urls,
                    summary=[],
                    keywords={},
                    error=str(e)
                )

    async def process_single_batch(
        self,
        image_urls: List[str],
        site: str = "auto"
    ) -> OCRChunkResult:
        """
        모든 이미지를 한 번에 처리 (청크 없이)

        Args:
            image_urls: 상세 이미지 URL 리스트
            site: 사이트

        Returns:
            OCRChunkResult: 처리 결과
        """
        if not image_urls:
            return OCRChunkResult(
                chunk_index=0,
                total_chunks=1,
                image_urls=[],
                summary=["처리할 이미지가 없습니다."],
                keywords={},
                is_final=True
            )

        try:
            result = await self._process_chunk(image_urls, site, 0)
            result.total_chunks = 1
            result.is_final = True
            return result

        except Exception as e:
            logger.error(f"OCR 처리 실패: {e}")
            return OCRChunkResult(
                chunk_index=0,
                total_chunks=1,
                image_urls=image_urls,
                summary=[],
                keywords={},
                is_final=True,
                error=str(e)
            )


# 싱글톤 인스턴스
_ocr_integrator: Optional[OCRIntegrator] = None


def get_ocr_integrator(
    chunk_size: int = 3,
    output_dir: str = "output"
) -> OCRIntegrator:
    """OCR 통합 서비스 인스턴스 반환"""
    global _ocr_integrator
    if _ocr_integrator is None:
        _ocr_integrator = OCRIntegrator(
            chunk_size=chunk_size,
            output_dir=output_dir
        )
    return _ocr_integrator
