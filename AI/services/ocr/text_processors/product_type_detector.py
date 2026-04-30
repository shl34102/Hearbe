# 상품 유형 분류 및 키워드 정의
import re
from enum import Enum
from typing import List, Dict, Optional


class ProductType(str, Enum):
    과자_스낵 = "과자_스낵"
    음료 = "음료"
    즉석식품 = "즉석식품"
    신선식품 = "신선식품"
    유제품 = "유제품"
    조미료_소스 = "조미료_소스"
    베이커리 = "베이커리"
    건강기능식품 = "건강기능식품"
    의약품 = "의약품"
    개인위생용품 = "개인위생용품"
    주방용품 = "주방용품"
    청소용품 = "청소용품"
    생활용품 = "생활용품"
    가전제품 = "가전제품"
    의류 = "의류"
    신발 = "신발"
    패션잡화 = "패션잡화"
    화장품 = "화장품"
    헤어케어 = "헤어케어"
    유아식품 = "유아식품"
    기저귀_물티슈 = "기저귀_물티슈"
    육아용품 = "육아용품"
    반려동물사료 = "반려동물사료"
    반려동물용품 = "반려동물용품"
    도서 = "도서"
    문구류 = "문구류"
    완구 = "완구"
    스포츠용품 = "스포츠용품"
    전자기기 = "전자기기"
    기타 = "기타"


TYPE_KEYWORDS: Dict[ProductType, List[str]] = {
    ProductType.과자_스낵: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "알레르기", "보관방법", "유통기한", "영양정보", "주의사항", "맛/특징"
    ],
    ProductType.음료: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "알레르기", "보관방법", "유통기한", "영양정보", "주의사항", "맛/특징", "카페인함량"
    ],
    ProductType.즉석식품: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "알레르기", "보관방법", "유통기한", "영양정보", "주의사항", "조리방법"
    ],
    ProductType.신선식품: [
        "가격", "제품명", "원산지", "중량/용량", "보관방법", "유통기한", "등급/품질"
    ],
    ProductType.유제품: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "알레르기", "보관방법", "유통기한", "영양정보", "주의사항"
    ],
    ProductType.조미료_소스: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "알레르기", "보관방법", "유통기한", "사용방법"
    ],
    ProductType.베이커리: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "알레르기", "보관방법", "유통기한", "영양정보"
    ],
    ProductType.건강기능식품: [
        "가격", "제품명", "브랜드", "중량/용량", "성분/함량",
        "섭취방법", "섭취주의사항", "유통기한", "기능성내용", "보관방법"
    ],
    ProductType.의약품: [
        "가격", "제품명", "효능/효과", "용법/용량", "성분",
        "사용상주의사항", "유통기한", "보관방법"
    ],
    ProductType.개인위생용품: [
        "가격", "제품명", "브랜드", "중량/용량", "성분",
        "사용방법", "주의사항", "유통기한"
    ],
    ProductType.주방용품: [
        "가격", "제품명", "브랜드", "재질", "크기/용량",
        "사용방법", "세척방법", "주의사항", "원산지"
    ],
    ProductType.청소용품: [
        "가격", "제품명", "브랜드", "중량/용량", "성분",
        "사용방법", "주의사항", "용도"
    ],
    ProductType.생활용품: [
        "가격", "제품명", "브랜드", "재질", "크기/수량",
        "사용방법", "주의사항"
    ],
    ProductType.가전제품: [
        "가격", "제품명", "브랜드", "모델명", "사양/스펙",
        "전력소비량", "크기/무게", "보증기간", "사용방법", "주의사항", "원산지"
    ],
    ProductType.의류: [
        "가격", "제품명", "브랜드", "사이즈", "소재/원단",
        "색상", "세탁방법", "원산지", "주의사항"
    ],
    ProductType.신발: [
        "가격", "제품명", "브랜드", "사이즈", "소재",
        "색상", "관리방법", "원산지"
    ],
    ProductType.패션잡화: [
        "가격", "제품명", "브랜드", "재질", "크기",
        "색상", "관리방법", "원산지"
    ],
    ProductType.화장품: [
        "가격", "제품명", "브랜드", "용량", "성분",
        "사용방법", "효능/효과", "유통기한", "주의사항", "피부타입"
    ],
    ProductType.헤어케어: [
        "가격", "제품명", "브랜드", "용량", "성분",
        "사용방법", "효능/효과", "유통기한", "주의사항", "모발타입"
    ],
    ProductType.유아식품: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "알레르기", "보관방법", "유통기한", "영양정보", "섭취방법", "적정월령"
    ],
    ProductType.기저귀_물티슈: [
        "가격", "제품명", "브랜드", "사이즈", "수량",
        "적용체중", "특징", "주의사항"
    ],
    ProductType.육아용품: [
        "가격", "제품명", "브랜드", "재질", "크기",
        "사용방법", "주의사항", "적정연령"
    ],
    ProductType.반려동물사료: [
        "가격", "제품명", "브랜드", "중량/용량", "원재료/성분",
        "급여방법", "보관방법", "유통기한", "적정연령/체중", "주의사항"
    ],
    ProductType.반려동물용품: [
        "가격", "제품명", "브랜드", "재질", "크기",
        "사용방법", "주의사항", "적정크기/종"
    ],
    ProductType.도서: [
        "가격", "제목", "저자", "출판사", "페이지수",
        "ISBN", "출판일", "내용소개"
    ],
    ProductType.문구류: [
        "가격", "제품명", "브랜드", "재질", "크기/수량",
        "색상", "용도", "주의사항"
    ],
    ProductType.완구: [
        "가격", "제품명", "브랜드", "재질", "크기",
        "적정연령", "주의사항", "KC인증"
    ],
    ProductType.스포츠용품: [
        "가격", "제품명", "브랜드", "재질", "크기/사이즈",
        "용도", "사용방법", "주의사항"
    ],
    ProductType.전자기기: [
        "가격", "제품명", "브랜드", "모델명", "사양/스펙",
        "배터리/전력", "크기/무게", "보증기간", "사용방법", "주의사항"
    ],
    ProductType.기타: [
        "가격", "제품명", "브랜드", "특징", "사용방법", "주의사항"
    ],
}


TYPE_DETECTION_KEYWORDS: Dict[ProductType, List[str]] = {
    ProductType.과자_스낵: [
        "과자", "스낵", "비스킷", "쿠키", "초콜릿", "사탕", "젤리", "껌",
        "칩", "크래커", "웨하스", "파이", "캔디"
    ],
    ProductType.음료: [
        "음료", "주스", "커피", "차", "탄산", "물", "두유", "소주", "맥주", "와인", "주류",
        "이온음료", "에너지드링크", "음료수", "드링크"
    ],
    ProductType.즉석식품: [
        "라면", "즉석", "컵라면", "레토르트", "냉동", "즉석밥", "즉석국",
        "즉석식품", "간편식", "HMR"
    ],
    ProductType.신선식품: [
        "신선", "과일", "채소", "육류", "수산물", "정육", "생선",
        "야채", "고기", "해산물",
        "삼겹살", "오겹살", "목살", "갈비", "등심", "안심", "차돌박이",
        "돼지고기", "소고기", "닭고기", "한우", "수입산", "국내산", "양념육",
        "다짐육", "불고기", "제육", "스테이크", "돈까스용", "국거리", "찌개용",
        "앞다리살", "뒷다리살", "항정살", "가브리살", "살치살", "채끝", "부채살",
        "고등어", "오징어", "새우", "전복", "갈치", "조기", "굴비", "멸치",
        "김", "미역", "다시마", "낙지", "쭈꾸미", "문어", "게", "꽃게", "대게",
        "킹크랩", "랍스터", "회", "연어", "광어", "우럭",
        "사과", "배", "포도", "귤", "딸기", "바나나", "키위", "토마토",
        "감자", "고구마", "양파", "파", "마늘", "고추", "상추", "깻잎",
        "배추", "무", "당근", "버섯"
    ],
    ProductType.유제품: [
        "유제품", "우유", "요거트", "치즈", "버터", "생크림", "요구르트"
    ],
    ProductType.조미료_소스: [
        "조미료", "소스", "간장", "고추장", "된장", "식초", "기름",
        "드레싱", "양념", "참기름", "케첩", "마요네즈"
    ],
    ProductType.베이커리: [
        "빵", "케이크", "베이커리", "도넛", "머핀", "식빵", "크루아상"
    ],
    ProductType.건강기능식품: [
        "영양제", "비타민", "건강기능식품", "프로바이오틱스", "오메가",
        "유산균", "홍삼", "보충제", "건강식품"
    ],
    ProductType.의약품: [
        "의약품", "약", "진통제", "감기약", "소화제", "연고", "파스"
    ],
    ProductType.개인위생용품: [
        "치약", "칫솔", "비누", "바디워시", "면도",
        "생리대", "위생용품", "구강", "데오드란트"
    ],
    ProductType.주방용품: [
        "주방", "냄비", "프라이팬", "그릇", "접시", "수저", "컵",
        "식기", "조리도구", "칼", "도마"
    ],
    ProductType.청소용품: [
        "세제", "청소", "세탁", "표백제", "섬유유연제", "락스",
        "주방세제", "세정제", "클리너"
    ],
    ProductType.생활용품: [
        "수건", "타월", "휴지", "화장지", "물티슈", "쓰레기봉투",
        "행주", "키친타월", "생활용품"
    ],
    ProductType.가전제품: [
        "가전", "전자레인지", "청소기", "선풍기", "에어컨", "냉장고",
        "세탁기", "건조기", "공기청정기", "가습기", "제습기"
    ],
    ProductType.의류: [
        "의류", "옷", "티셔츠", "셔츠", "바지", "치마", "원피스",
        "자켓", "코트", "패딩", "니트", "후드", "팬츠", "SIZE",
        "사이즈", "허리둘레", "총장", "와이드", "슬랙스", "청바지",
        # 소재 키워드는 더 구체적으로 (단독 "면"은 "측면" 등과 혼동)
        "면100", "순면", "폴리에스터", "폴리100", "드라이클리닝"
    ],
    ProductType.신발: [
        "신발", "운동화", "구두", "슬리퍼", "샌들", "부츠", "스니커즈"
    ],
    ProductType.패션잡화: [
        "가방", "모자", "벨트", "지갑", "목도리", "장갑", "양말",
        "스카프", "넥타이"
    ],
    ProductType.화장품: [
        "화장품", "스킨", "로션", "크림", "에센스", "세럼", "팩",
        "마스크", "선크림", "파운데이션", "립스틱", "아이섀도우",
        "메이크업", "코스메틱"
    ],
    ProductType.헤어케어: [
        "헤어", "샴푸", "린스", "트리트먼트", "헤어팩", "염색",
        "왁스", "스프레이", "헤어오일", "두피", "모발", "탈모",
        "스칼프", "케라틴", "컨디셔너", "헤어케어", "케어샴푸"
    ],
    ProductType.유아식품: [
        "유아식", "분유", "이유식", "아기", "베이비", "유아"
    ],
    ProductType.기저귀_물티슈: [
        "기저귀", "밴드", "팬티형", "아기물티슈"
    ],
    ProductType.육아용품: [
        "젖병", "젖꼭지", "유축기", "아기띠", "유모차", "카시트",
        "아기용품", "육아"
    ],
    ProductType.반려동물사료: [
        "사료", "강아지", "고양이", "반려동물", "펫", "간식"
    ],
    ProductType.반려동물용품: [
        "애견", "애묘", "펫용품", "목줄", "장난감", "하우스", "화장실"
    ],
    ProductType.도서: [
        "도서", "책", "서적", "소설", "만화", "잡지", "교재"
    ],
    ProductType.문구류: [
        "문구", "펜", "연필", "노트", "공책", "지우개", "자",
        "풀", "테이프", "스티커"
    ],
    ProductType.완구: [
        "장난감", "완구", "인형", "블록", "레고", "피규어", "보드게임"
    ],
    ProductType.스포츠용품: [
        "운동", "스포츠", "헬스", "요가", "수영", "등산", "자전거",
        "골프", "야구", "축구", "농구"
    ],
    ProductType.전자기기: [
        "전자기기", "스마트폰", "태블릿", "이어폰", "헤드폰", "충전기",
        "케이블", "마우스", "키보드", "스피커"
    ],
}


TYPE_DESCRIPTIONS: Dict[ProductType, str] = {
    ProductType.과자_스낵: "과자/스낵류",
    ProductType.음료: "음료",
    ProductType.즉석식품: "즉석식품",
    ProductType.신선식품: "신선식품",
    ProductType.유제품: "유제품",
    ProductType.조미료_소스: "조미료/소스",
    ProductType.베이커리: "베이커리",
    ProductType.건강기능식품: "건강기능식품/영양제",
    ProductType.의약품: "의약품",
    ProductType.개인위생용품: "개인위생용품",
    ProductType.주방용품: "주방용품",
    ProductType.청소용품: "청소용품",
    ProductType.생활용품: "생활용품",
    ProductType.가전제품: "가전제품",
    ProductType.의류: "의류",
    ProductType.신발: "신발",
    ProductType.패션잡화: "패션잡화",
    ProductType.화장품: "화장품",
    ProductType.헤어케어: "헤어케어",
    ProductType.유아식품: "유아식품",
    ProductType.기저귀_물티슈: "기저귀/물티슈",
    ProductType.육아용품: "육아용품",
    ProductType.반려동물사료: "반려동물 사료",
    ProductType.반려동물용품: "반려동물 용품",
    ProductType.도서: "도서",
    ProductType.문구류: "문구류",
    ProductType.완구: "완구",
    ProductType.스포츠용품: "스포츠용품",
    ProductType.전자기기: "전자기기",
    ProductType.기타: "기타",
}


# "식품유형" 라벨 → ProductType 매핑 (OCR에서 직접 추출된 정보 우선)
FOOD_TYPE_LABEL_MAP: Dict[str, ProductType] = {
    # 빵류
    "빵류": ProductType.베이커리,
    "빵": ProductType.베이커리,
    "베이커리": ProductType.베이커리,
    "케이크류": ProductType.베이커리,
    # 과자류
    "과자": ProductType.과자_스낵,
    "과자류": ProductType.과자_스낵,
    "스낵": ProductType.과자_스낵,
    "스낵류": ProductType.과자_스낵,
    "비스킷": ProductType.과자_스낵,
    "비스킷류": ProductType.과자_스낵,
    "캔디류": ProductType.과자_스낵,
    "초콜릿류": ProductType.과자_스낵,
    # 음료류
    "음료": ProductType.음료,
    "음료류": ProductType.음료,
    "탄산음료": ProductType.음료,
    "과채음료": ProductType.음료,
    "과채주스": ProductType.음료,
    "커피": ProductType.음료,
    "다류": ProductType.음료,
    # 면류/즉석식품
    "면류": ProductType.즉석식품,
    "라면": ProductType.즉석식품,
    "즉석식품": ProductType.즉석식품,
    "즉석조리식품": ProductType.즉석식품,
    "레토르트식품": ProductType.즉석식품,
    "냉동식품": ProductType.즉석식품,
    # 유제품
    "유가공품": ProductType.유제품,
    "유제품": ProductType.유제품,
    "우유류": ProductType.유제품,
    "발효유": ProductType.유제품,
    "발효유류": ProductType.유제품,
    "치즈류": ProductType.유제품,
    "아이스크림": ProductType.유제품,
    "아이스크림류": ProductType.유제품,
    # 조미료/소스
    "조미식품": ProductType.조미료_소스,
    "소스": ProductType.조미료_소스,
    "소스류": ProductType.조미료_소스,
    "장류": ProductType.조미료_소스,
    "식용유지": ProductType.조미료_소스,
    "드레싱": ProductType.조미료_소스,
    # 건강기능식품
    "건강기능식품": ProductType.건강기능식품,
    # 신선식품/농산물
    "농산물": ProductType.신선식품,
    "수산물": ProductType.신선식품,
    "축산물": ProductType.신선식품,
    "식육": ProductType.신선식품,
    "식육가공품": ProductType.신선식품,
}


def extract_food_type_label(texts: List[str]) -> Optional[ProductType]:
    """
    OCR 텍스트에서 "식품유형" 라벨을 추출하여 ProductType 반환
    예: "식품유형빵류원재료명..." → ProductType.베이커리
    """
    combined = "".join(texts)  # 공백 없이 합침 (OCR 결과가 붙어있을 수 있음)

    # "식품유형" 다음에 오는 텍스트 추출
    # 패턴: 식품유형 + 타입명 + (원재료명|제조원|판매원|유통|내용량 등)
    pattern = r"식품유형\s*[:：]?\s*([가-힣]+?)(?:원재료|제조|판매|유통|내용|성분|영양|보관|주의|알레르기|원산지|$)"
    match = re.search(pattern, combined)

    if match:
        food_type = match.group(1).strip()
        # 매핑 테이블에서 찾기
        if food_type in FOOD_TYPE_LABEL_MAP:
            return FOOD_TYPE_LABEL_MAP[food_type]
        # 부분 매칭 시도 (예: "빵류원재료명" → "빵류")
        for label, ptype in FOOD_TYPE_LABEL_MAP.items():
            if label in food_type or food_type in label:
                return ptype

    return None


CORE_KEYWORD_WEIGHTS: Dict[ProductType, Dict[str, int]] = {
    ProductType.과자_스낵: {
        "과자": 5, "스낵": 5, "쿠키": 5, "비스킷": 5, "초콜릿": 5,
        "사탕": 4, "젤리": 4, "껌": 4, "칩": 4, "크래커": 4,
    },
    ProductType.음료: {
        "음료": 5, "주스": 5, "커피": 4, "탄산": 4, "드링크": 4,
    },
    ProductType.즉석식품: {
        "라면": 5, "즉석": 4, "컵라면": 5, "레토르트": 5, "HMR": 5,
    },
    ProductType.의류: {
        "SIZE": 10, "사이즈": 10, "허리둘레": 5, "총장": 5, "팬츠": 5,
        "바지": 5, "티셔츠": 5, "셔츠": 5, "원피스": 5, "치마": 5,
        "와이드": 4, "슬랙스": 4, "면100": 4, "순면": 4, "폴리에스터": 4,
        "M": 2, "L": 2, "XL": 2, "FREE": 3,
    },
    ProductType.헤어케어: {
        "샴푸": 5, "린스": 5, "트리트먼트": 5, "두피": 4, "모발": 4,
        "탈모": 4, "스칼프": 4, "헤어케어": 5, "케어샴푸": 5, "컨디셔너": 5,
        "헤어": 3, "헤어팩": 4, "염색": 3, "케라틴": 4, "헤어오일": 4,
    },
    ProductType.개인위생용품: {
        "치약": 5, "칫솔": 5, "비누": 4, "바디워시": 4, "면도": 5,
        "생리대": 5, "위생용품": 4, "구강": 4, "데오드란트": 5,
    },
}


def detect_product_type(texts: List[str]) -> ProductType:
    # 1순위: "식품유형" 라벨에서 직접 추출 (가장 신뢰도 높음)
    food_type = extract_food_type_label(texts)
    if food_type:
        return food_type

    # 2순위: 키워드 기반 감지
    combined_text = " ".join(texts).lower()
    scores: Dict[ProductType, float] = {}

    for ptype, keywords in TYPE_DETECTION_KEYWORDS.items():
        score = 0.0
        weights = CORE_KEYWORD_WEIGHTS.get(ptype, {})

        for keyword in keywords:
            if keyword.lower() in combined_text:
                weight = weights.get(keyword, 1)
                score += weight

        if score > 0:
            scores[ptype] = score

    if scores:
        detected_type = max(scores, key=scores.get)
        return detected_type

    return ProductType.기타


def get_keywords_for_type(product_type: ProductType) -> List[str]:
    return TYPE_KEYWORDS.get(product_type, TYPE_KEYWORDS[ProductType.기타])


def get_type_description(product_type: ProductType) -> str:
    return TYPE_DESCRIPTIONS.get(product_type, "기타")


def is_keyword_valid_for_type(product_type: ProductType, keyword: str) -> bool:
    valid_keywords = get_keywords_for_type(product_type)
    return keyword in valid_keywords


# 타입 오버라이드 규칙
_TYPE_OVERRIDE_RULES = {
    "electronics": {
        "strong": ("HDMI", "IPS", "FHD"),
        "weak": ("Hz", "인치", "모니터", "디스플레이"),
    },
    "fresh_food": {
        "strong": ("유통기한", "보관", "냉장", "냉동"),
        "weak": ("산지", "제철"),
    },
}


def _find_type_by_description(fragment: str) -> Optional[ProductType]:
    """설명에 특정 문자열이 포함된 ProductType 찾기"""
    for pt in ProductType:
        if fragment in get_type_description(pt):
            return pt
    return None


def override_product_type(
    texts: List[str],
    current_type: ProductType
) -> ProductType:
    """OCR 텍스트 기반으로 제품 타입 오버라이드"""
    joined = " ".join(texts)

    # SIZE 관련 키워드가 있으면 무조건 의류로 판단
    # SIZE 관련 키워드가 있으면 무조건 의류로 판단
    size_keywords = [
        "SIZE", "사이즈", "허리", "총장", "영덩이", "왓밀위", "뜻밀위", "밀단",
        "가슴둘레", "어깨너비", "소매길이", "기장", "밑단"
    ]
    size_labels = ["S", "M", "L", "XL", "2XL", "3XL", "FREE"]

    # 1. SIZE 키워드 감지
    has_size_keyword = any(kw in joined.upper() for kw in size_keywords)
    
    # 2. 사이즈 라벨 개수 카운트 (M, L, XL 등이 여러 개 나오면 의류일 확률 높음)
    # 단, 단순 알파벳과의 혼동을 막기 위해 독립된 토큰으로 확인
    label_count = 0
    upper_joined = f" {joined.upper()} "  # 앞뒤 공백 추가
    for label in size_labels:
        if f" {label} " in upper_joined or f"|{label}|" in upper_joined:
            label_count += 1

    # 조건 완화:
    # 1) 키워드와 라벨이 모두 있는 경우 (확실)
    # 2) 사이즈 라벨이 3개 이상 발견된 경우 (키워드 없어도 표로 추정)
    if (has_size_keyword and label_count >= 1) or (label_count >= 3):
        return ProductType.의류

    scores = {}
    strong_hits = {}

    for key, rules in _TYPE_OVERRIDE_RULES.items():
        strong = rules["strong"]
        weak = rules["weak"]
        s_hits = sum(1 for token in strong if token in joined)
        w_hits = sum(1 for token in weak if token in joined)
        strong_hits[key] = s_hits
        scores[key] = s_hits * 3 + w_hits

    # strong 키워드 2개 이상 매칭 시 타입 오버라이드
    if strong_hits["electronics"] >= 2:
        pt = _find_type_by_description("전자")
        if pt:
            return pt
    if strong_hits["fresh_food"] >= 2:
        pt = _find_type_by_description("신선")
        if pt:
            return pt

    # 점수 차이가 충분히 클 때 오버라이드
    if scores["electronics"] - scores["fresh_food"] >= 2 and scores["electronics"] >= 4:
        pt = _find_type_by_description("전자")
        if pt:
            return pt
    if scores["fresh_food"] - scores["electronics"] >= 2 and scores["fresh_food"] >= 4:
        pt = _find_type_by_description("신선")
        if pt:
            return pt

    return current_type
