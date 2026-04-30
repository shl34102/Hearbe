"""
NLU 서비스 구현

의도 분석, 개체명 인식, 대명사 참조 해석
"""

import logging
from typing import Dict, Any, List
from core.interfaces import INLUService, IntentResult, IntentType, NEREntity
from core.config import get_config

logger = logging.getLogger(__name__)


# 쇼핑 관련 의도 패턴
INTENT_PATTERNS = {
    IntentType.SEARCH: [
        "찾아줘", "검색해줘", "보여줘", "있어?", "뭐 있어",
        "찾아", "검색", "보여", "있나", "알려줘"
    ],
    IntentType.ADD_TO_CART: [
        "장바구니", "담아", "담아줘", "카트에", "추가해"
    ],
    IntentType.CHECKOUT: [
        "결제", "구매", "주문", "살게", "살래", "계산"
    ],
    IntentType.COMPARE: [
        "비교", "뭐가 나아", "어떤 게", "차이가"
    ],
    IntentType.SELECT_ITEM: [
        "첫 번째", "두 번째", "세 번째", "그거", "이거", "저거",
        "첫째", "둘째", "셋째", "넷째", "다섯째",
        "여섯째", "일곱째", "여덟째", "아홉째", "열째",
        "제일", "맨 위", "맨 아래"
    ],
    IntentType.ASK_INFO: [
        "얼마", "가격", "배송", "언제", "리뷰", "평점",
        "유통기한", "소비기한", "사이즈", "색상"
    ],
    IntentType.CONFIRM: [
        "응", "네", "맞아", "좋아", "그래", "확인", "진행"
    ],
    IntentType.CANCEL: [
        "아니", "취소", "안 해", "그만", "돌아가"
    ],
    IntentType.SIGNUP: [
        "회원가입", "가입"
    ],
    IntentType.LOGIN: [
        "로그인"
    ],
}


class NLUService(INLUService):
    """
    자연어 이해 서비스

    Features:
    - 쇼핑 의도 분석
    - 상품명, 브랜드, 가격 등 개체명 인식
    - 대명사 참조 해석 ("그거", "두 번째 거")
    """

    def __init__(self):
        self._config = get_config().nlu

    async def initialize(self):
        """서비스 초기화"""
        logger.info("NLU service initialized")

    async def analyze_intent(
        self,
        text: str,
        context: Dict[str, Any] = None
    ) -> IntentResult:
        """
        사용자 발화에서 의도 분석

        Args:
            text: 사용자 발화 텍스트
            context: 대화 컨텍스트

        Returns:
            IntentResult: 의도 분석 결과
        """
        if context is None:
            context = {}

        text_lower = text.lower()
        detected_intent = IntentType.UNKNOWN
        confidence = 0.0

        # 패턴 매칭으로 의도 파악
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    detected_intent = intent
                    confidence = 0.8
                    break
            if detected_intent != IntentType.UNKNOWN:
                break

        # 개체명 추출
        entities = await self.extract_entities(text)
        entity_dict = {e.entity_type: e.value for e in entities}

        logger.debug(f"Intent: {detected_intent.value}, entities: {entity_dict}")

        return IntentResult(
            intent=detected_intent,
            confidence=confidence,
            entities=entity_dict,
            raw_text=text
        )

    async def extract_entities(self, text: str) -> List[NEREntity]:
        """
        개체명 인식 (NER)

        추출 대상:
        - product_name: 상품명
        - brand: 브랜드
        - price: 가격/가격 범위
        - quantity: 수량
        - category: 카테고리

        Args:
            text: 분석할 텍스트

        Returns:
            List[NEREntity]: 추출된 개체 목록
        """
        entities = []

        # TODO: 실제 NER 모델 또는 LLM 기반 추출
        # 현재는 간단한 규칙 기반 예시

        # 가격 패턴 ("10만원", "5000원 이하")
        import re
        price_pattern = r'(\d+(?:,\d+)?)\s*(?:만\s*)?원(?:\s*(이하|이상|미만|대))?'
        price_matches = re.finditer(price_pattern, text)
        for match in price_matches:
            entities.append(NEREntity(
                entity_type="price",
                value=match.group(0),
                start=match.start(),
                end=match.end()
            ))

        # 수량 패턴 ("2개", "세 개")
        quantity_pattern = r'(\d+|한|두|세|네|다섯)\s*개'
        quantity_matches = re.finditer(quantity_pattern, text)
        for match in quantity_matches:
            entities.append(NEREntity(
                entity_type="quantity",
                value=match.group(0),
                start=match.start(),
                end=match.end()
            ))

        return entities

    async def resolve_reference(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> str:
        """
        대명사/참조 해석

        "그거" → 이전 검색 결과의 첫 번째 상품
        "두 번째 거" → 이전 검색 결과의 두 번째 상품

        Args:
            text: 원본 텍스트
            context: 이전 검색 결과 등의 컨텍스트

        Returns:
            str: 해석된 텍스트
        """
        search_results = context.get("search_results", [])

        if not search_results:
            return text

        # 순서 참조 해석
        ordinal_map = {
            "첫 번째": 0, "첫번째": 0, "처음": 0, "맨 위": 0, "제일 위": 0,
            "두 번째": 1, "두번째": 1,
            "세 번째": 2, "세번째": 2,
            "네 번째": 3, "네번째": 3,
            "다섯 번째": 4, "다섯번째": 4,
            "첫째": 0, "둘째": 1, "셋째": 2, "넷째": 3, "다섯째": 4,
            "여섯째": 5, "일곱째": 6, "여덟째": 7, "아홉째": 8, "열째": 9,
            "마지막": -1, "맨 아래": -1, "제일 아래": -1,
        }

        resolved_text = text
        for ref, idx in ordinal_map.items():
            if ref in text and len(search_results) > abs(idx):
                product = search_results[idx]
                product_name = product.get("name", "")
                resolved_text = text.replace(ref, product_name)
                break

        # "그거", "이거" 해석 (가장 최근 언급된 상품)
        if "그거" in text or "이거" in text:
            last_mentioned = context.get("last_mentioned_product")
            if last_mentioned:
                resolved_text = text.replace("그거", last_mentioned).replace("이거", last_mentioned)

        logger.debug(f"Resolved '{text}' -> '{resolved_text}'")
        return resolved_text

    async def shutdown(self):
        """리소스 정리"""
        logger.info("NLU service shutdown")
