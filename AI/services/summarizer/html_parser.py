# -*- coding: utf-8 -*-
"""
HTML Parser for Product Pages

MCP에서 받은 HTML 데이터를 파싱하여 상품 정보를 추출합니다.
OCR 없이 바로 얻을 수 있는 텍스트 정보를 빠르게 파싱합니다.
"""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from core.korean_product_terms import format_product_terms_for_tts

logger = logging.getLogger(__name__)


@dataclass
class ProductInfo:
    """상품 정보 데이터 클래스"""
    product_name: str = ""
    price: str = ""
    original_price: str = ""
    discount_rate: str = ""
    delivery_info: str = ""
    arrival_info: str = ""
    free_shipping: bool = False
    free_return: bool = False
    rating: str = ""
    review_count: str = ""
    seller: str = ""
    options: List[str] = field(default_factory=list)
    detail_images: List[str] = field(default_factory=list)
    extra_info: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "price": self.price,
            "original_price": self.original_price,
            "discount_rate": self.discount_rate,
            "delivery_info": self.delivery_info,
            "arrival_info": self.arrival_info,
            "free_shipping": self.free_shipping,
            "free_return": self.free_return,
            "rating": self.rating,
            "review_count": self.review_count,
            "seller": self.seller,
            "options": self.options,
            "detail_images": self.detail_images,
            "extra_info": self.extra_info,
        }

    def is_valid(self) -> bool:
        """최소한의 정보가 있는지 확인"""
        return bool(self.product_name or self.price)


class BaseHTMLParser(ABC):
    """HTML 파서 기본 클래스"""

    @abstractmethod
    def parse(self, html: str) -> ProductInfo:
        """HTML을 파싱하여 ProductInfo 반환"""
        pass

    @abstractmethod
    def get_site_name(self) -> str:
        """사이트 이름 반환"""
        pass

    def _clean_text(self, text: Optional[str]) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_number(self, text: str) -> str:
        """숫자 추출 (가격, 수량 등)"""
        if not text:
            return ""
        numbers = re.findall(r'[\d,]+', text)
        return numbers[0] if numbers else ""

    def _parse_price(self, text: str) -> str:
        """가격 파싱 (원화)"""
        if not text:
            return ""
        price = self._extract_number(text)
        if price:
            return f"{price}원"
        return ""


class CoupangHTMLParser(BaseHTMLParser):
    """
    쿠팡 상품 페이지 HTML 파서

    지원하는 셀렉터:
    - .product-title__name: 상품명
    - .final-price, .total-price: 가격
    - .origin-price: 원가
    - .discount-rate: 할인율
    - .delivery-date: 배송 정보
    - .rating-count: 리뷰 수
    - .prod-option: 옵션 정보
    - .product-detail-content-inside img: 상세 이미지
    """

    SELECTORS = {
        "product_name": [
            ".product-title__name",
            "h1.prod-buy-header__title",
            ".prod-buy-header__title",
            ".ProductUnit_productNameV2__cV9cw",
        ],
        "price": [
            ".total-price strong",
            ".final-price",
            ".prod-sale-price .total-price",
            ".PriceArea_priceArea__NntJz .fw-text-red-700",
        ],
        "original_price": [
            ".origin-price",
            ".base-price",
            ".PriceArea_priceArea__NntJz del",
        ],
        "discount_rate": [
            ".discount-rate",
            ".discount-percentage",
        ],
        "delivery_info": [
            ".delivery-date",
            ".prod-shipping-fee-message",
            ".rocket-delivery-info",
        ],
        "review_count": [
            ".rating-count",
            ".prod-review-count",
        ],
        "rating": [
            ".rating-score",
            ".star-rating",
        ],
        "seller": [
            ".prod-sale-vendor-name",
            ".seller-name",
        ],
        "options": [
            ".prod-option__item",
            ".prod-option-dropdown-item",
        ],
        "detail_images": [
            ".product-detail-content-inside img",
            ".product-detail img",
            "#productDetail img",
        ],
    }

    def get_site_name(self) -> str:
        return "쿠팡"

    def parse(self, html: str) -> ProductInfo:
        """쿠팡 HTML 파싱"""
        if not html:
            return ProductInfo()

        try:
            soup = BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"HTML 파싱 실패: {e}")
            return ProductInfo()

        info = ProductInfo()

        # 상품명
        info.product_name = self._find_first(soup, self.SELECTORS["product_name"])

        # 가격
        price_text = self._find_first(soup, self.SELECTORS["price"])
        info.price = self._parse_price(price_text)

        # 원가
        original_text = self._find_first(soup, self.SELECTORS["original_price"])
        info.original_price = self._parse_price(original_text)

        # 할인율
        info.discount_rate = self._find_first(soup, self.SELECTORS["discount_rate"])
        if not info.discount_rate:
            info.discount_rate = self._find_percent_in_area(soup, ".PriceArea_priceArea__NntJz")

        # 배송 정보
        info.delivery_info = self._find_first(soup, self.SELECTORS["delivery_info"])
        info.arrival_info = self._find_arrival_info(soup)
        info.free_shipping = self._has_text(soup, "무료배송")
        info.free_return = self._has_text(soup, "무료반품")

        # 리뷰 수
        review_text = self._find_first(soup, self.SELECTORS["review_count"])
        info.review_count = self._extract_number(review_text)

        # 평점
        info.rating = self._find_first(soup, self.SELECTORS["rating"])

        # 판매자
        info.seller = self._find_first(soup, self.SELECTORS["seller"])

        # 옵션
        info.options = self._find_all(soup, self.SELECTORS["options"])

        # 상세 이미지 URL
        info.detail_images = self._find_images(soup, self.SELECTORS["detail_images"])

        logger.debug(f"쿠팡 파싱 완료: {info.product_name}, 이미지 {len(info.detail_images)}개")

        return info

    def _find_first(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """여러 셀렉터 중 첫 번째로 매칭되는 텍스트 반환"""
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return self._clean_text(elem.get_text())
        return ""

    def _find_all(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """여러 셀렉터로 모든 매칭 텍스트 반환"""
        results = []
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = self._clean_text(elem.get_text())
                if text and text not in results:
                    results.append(text)
        return results

    def _find_images(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """이미지 URL 추출"""
        images = []
        seen = set()

        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                src = elem.get('src') or elem.get('data-src') or elem.get('data-lazy-src')
                if src and src not in seen:
                    # 상대 경로를 절대 경로로 변환
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://www.coupang.com' + src

                    # 광고/아이콘 필터링
                    if not self._is_valid_product_image(src):
                        continue

                    seen.add(src)
                    images.append(src)

        return images

    def _has_text(self, soup: BeautifulSoup, keyword: str) -> bool:
        """텍스트 포함 여부"""
        if not keyword:
            return False
        return bool(soup.find(string=re.compile(re.escape(keyword))))

    def _find_percent_in_area(self, soup: BeautifulSoup, area_selector: str) -> str:
        """특정 영역에서 퍼센트 텍스트 추출"""
        try:
            area = soup.select_one(area_selector)
        except Exception:
            area = None
        target = area if area else soup
        if not target:
            return ""
        text = self._clean_text(target.get_text())
        match = re.search(r"\d+\s*%", text)
        return match.group(0) if match else ""

    def _find_arrival_info(self, soup: BeautifulSoup) -> str:
        """도착 보장 정보 추출"""
        for div in soup.find_all("div"):
            text = self._clean_text(div.get_text(" "))
            if "도착" in text and ("보장" in text or "도착" in text):
                # 너무 긴 텍스트는 컷
                if len(text) > 60:
                    continue
                return text
        return ""
    def _is_valid_product_image(self, url: str) -> bool:
        """상품 상세 이미지인지 확인 (광고/아이콘 제외)"""
        exclude_patterns = [
            r'/banner/', r'/ad/', r'/icon/', r'/logo/',
            r'/button/', r'/badge/', r'static\.coupang',
            r'ads\.', r'pixel\.', r'/event/', r'/promotion/',
        ]
        url_lower = url.lower()
        return not any(re.search(p, url_lower) for p in exclude_patterns)


class NaverHTMLParser(BaseHTMLParser):
    """
    네이버 쇼핑 상품 페이지 HTML 파서

    지원하는 셀렉터:
    - ._3oDjSvLfl0: 상품명
    - ._1LY7DqCnwR: 가격
    - #INTRODUCE img: 상세 이미지
    """

    SELECTORS = {
        "product_name": [
            "._3oDjSvLfl0",
            ".product-title",
            "h2._3oDjSvLfl0",
        ],
        "price": [
            "._1LY7DqCnwR",
            ".product-price",
            "._1LY7DqCnwR strong",
        ],
        "original_price": [
            "._2RqnOL0OZR",
            ".origin-price",
        ],
        "discount_rate": [
            "._2RqnOL0OZR span",
            ".discount-rate",
        ],
        "delivery_info": [
            "._3H-4dFHHhW",
            ".delivery-info",
        ],
        "review_count": [
            "._2N_MalQHrs",
            ".review-count",
        ],
        "rating": [
            "._2N_MalQHrs span",
            ".star-rating",
        ],
        "seller": [
            "._1eXzNQrQjE",
            ".seller-name",
        ],
        "options": [
            "._3gkWoNS9Qu",
            ".option-item",
        ],
        "detail_images": [
            "#INTRODUCE img",
            ".product-detail img",
            "._3GXr9PxQD6 img",
        ],
    }

    def get_site_name(self) -> str:
        return "네이버"

    def parse(self, html: str) -> ProductInfo:
        """네이버 HTML 파싱"""
        if not html:
            return ProductInfo()

        try:
            soup = BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"HTML 파싱 실패: {e}")
            return ProductInfo()

        info = ProductInfo()

        # 상품명
        info.product_name = self._find_first(soup, self.SELECTORS["product_name"])

        # 가격
        price_text = self._find_first(soup, self.SELECTORS["price"])
        info.price = self._parse_price(price_text)

        # 원가
        original_text = self._find_first(soup, self.SELECTORS["original_price"])
        info.original_price = self._parse_price(original_text)

        # 할인율
        info.discount_rate = self._find_first(soup, self.SELECTORS["discount_rate"])

        # 배송 정보
        info.delivery_info = self._find_first(soup, self.SELECTORS["delivery_info"])

        # 리뷰 수
        review_text = self._find_first(soup, self.SELECTORS["review_count"])
        info.review_count = self._extract_number(review_text)

        # 평점
        info.rating = self._find_first(soup, self.SELECTORS["rating"])

        # 판매자
        info.seller = self._find_first(soup, self.SELECTORS["seller"])

        # 옵션
        info.options = self._find_all(soup, self.SELECTORS["options"])

        # 상세 이미지 URL
        info.detail_images = self._find_images(soup, self.SELECTORS["detail_images"])

        logger.debug(f"네이버 파싱 완료: {info.product_name}, 이미지 {len(info.detail_images)}개")

        return info

    def _find_first(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """여러 셀렉터 중 첫 번째로 매칭되는 텍스트 반환"""
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return self._clean_text(elem.get_text())
        return ""

    def _find_all(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """여러 셀렉터로 모든 매칭 텍스트 반환"""
        results = []
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = self._clean_text(elem.get_text())
                if text and text not in results:
                    results.append(text)
        return results

    def _find_images(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """이미지 URL 추출"""
        images = []
        seen = set()

        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                src = elem.get('src') or elem.get('data-src') or elem.get('data-lazy-src')
                if src and src not in seen:
                    if src.startswith('//'):
                        src = 'https:' + src

                    if not self._is_valid_product_image(src):
                        continue

                    seen.add(src)
                    images.append(src)

        return images

    def _is_valid_product_image(self, url: str) -> bool:
        """상품 상세 이미지인지 확인"""
        exclude_patterns = [
            r'/ad/', r'/banner/', r'/static/', r'/icon/',
            r'/logo/', r'adimg\.', r'ssl\.pstatic\.net/static',
        ]
        url_lower = url.lower()
        return not any(re.search(p, url_lower) for p in exclude_patterns)


def detect_site(url: str) -> str:
    """URL에서 사이트 감지"""
    if not url:
        return "unknown"
    url_lower = url.lower()
    if "coupang" in url_lower:
        return "coupang"
    elif "naver" in url_lower or "pstatic.net" in url_lower:
        return "naver"
    return "unknown"


def get_parser(site: str) -> BaseHTMLParser:
    """사이트에 맞는 파서 반환"""
    parsers = {
        "coupang": CoupangHTMLParser(),
        "naver": NaverHTMLParser(),
    }
    return parsers.get(site, CoupangHTMLParser())


def parse_product_html(
    html: str,
    site: str = "auto",
    url: str = ""
) -> ProductInfo:
    """
    상품 HTML을 파싱하여 ProductInfo 반환

    Args:
        html: 상품 페이지 HTML
        site: 사이트 (auto/coupang/naver)
        url: 페이지 URL (site가 auto일 때 사용)

    Returns:
        ProductInfo 객체
    """
    if site == "auto":
        site = detect_site(url)

    parser = get_parser(site)
    return parser.parse(html)


def format_for_tts(info: ProductInfo, include_details: bool = False) -> str:
    """
    ProductInfo를 TTS용 텍스트로 변환

    Args:
        info: 상품 정보
        include_details: 상세 정보 포함 여부

    Returns:
        TTS용 텍스트
    """
    if not info.is_valid():
        return "상품 정보를 찾을 수 없습니다."

    parts = []

    # 상품명
    if info.product_name:
        parts.append(f"{info.product_name}")

    # 가격/할인
    if info.price:
        if info.discount_rate:
            parts.append(f"{info.discount_rate} 할인 중이며 {info.price}입니다")
        else:
            parts.append(f"{info.price}입니다")

    # 배송/반품/도착
    if info.free_shipping:
        parts.append("무료배송")
    if info.free_return:
        parts.append("무료반품")
    if info.arrival_info:
        parts.append(info.arrival_info)
    elif info.delivery_info:
        parts.append(info.delivery_info)

    parts = [format_product_terms_for_tts(part) for part in parts]
    return ". ".join(parts) + "."


def format_summary_for_tts(info: ProductInfo) -> List[str]:
    """
    ProductInfo를 TTS용 요약 리스트로 변환

    Returns:
        요약 문장 리스트
    """
    summaries = []

    if info.product_name:
        summaries.append(f"{info.product_name}입니다.")

    if info.price:
        if info.discount_rate:
            summaries.append(f"{info.discount_rate} 할인 중이며 {info.price}입니다.")
        else:
            summaries.append(f"{info.price}입니다.")

    if info.free_shipping:
        summaries.append("무료배송입니다.")
    if info.free_return:
        summaries.append("무료반품입니다.")
    if info.arrival_info:
        summaries.append(f"{info.arrival_info}입니다.")
    elif info.delivery_info:
        summaries.append(f"{info.delivery_info}입니다.")

    summaries = [format_product_terms_for_tts(summary) for summary in summaries]
    return summaries if summaries else ["상품 정보를 찾을 수 없습니다."]
