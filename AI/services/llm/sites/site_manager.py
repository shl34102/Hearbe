"""
사이트 관리자 모듈 (페이지별 셀렉터 지원)

각 쇼핑몰의 셀렉터, URL, 규칙을 로딩하고 관리합니다.
현재 URL 기반으로 어떤 사이트/페이지에 있는지 판단하고, 해당 페이지의 셀렉터를 반환합니다.

디렉토리 구조:
  config/sites/coupang/
    index.json      - 사이트 정보
    main.json       - 메인 페이지 셀렉터
    product.json    - 상품 페이지 셀렉터
    cart.json       - 장바구니 페이지 셀렉터
    ...
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class PageSelectors:
    """단일 페이지의 셀렉터"""
    
    def __init__(self, data: Dict[str, Any]):
        self.page_type: str = data.get("page_type", "")
        self.url_pattern: str = data.get("url_pattern", "")
        self.description: str = data.get("description", "")
        self.selectors: Dict[str, str] = data.get("selectors", {})
    
    def matches_url(self, url: str) -> bool:
        """URL이 이 페이지 패턴과 매칭되는지 확인"""
        if not self.url_pattern or not url:
            return False
        try:
            return bool(re.search(self.url_pattern, url))
        except Exception:
            return False
    
    def get_selector(self, name: str) -> Optional[str]:
        """셀렉터 가져오기"""
        return self.selectors.get(name)


class SiteConfig:
    """단일 사이트 설정 (페이지별 셀렉터 포함)"""
    
    def __init__(self, site_id: str, index_data: Dict[str, Any], pages: Dict[str, PageSelectors]):
        self.site_id: str = site_id
        self.name: str = index_data.get("name", "")
        self.domains: List[str] = index_data.get("domains", [])
        self.urls: Dict[str, str] = index_data.get("urls", {})
        self.pages: Dict[str, PageSelectors] = pages  # page_type -> PageSelectors
    
    def get_url(self, name: str) -> Optional[str]:
        """URL 가져오기 (예: get_url("home"))"""
        return self.urls.get(name)
    
    def matches_domain(self, url: str) -> bool:
        """URL이 이 사이트에 속하는지 확인"""
        if not url:
            return False
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            for domain in self.domains:
                if domain in host:
                    return True
        except Exception:
            pass
        return False
    
    def detect_page_type(self, url: str) -> Optional[str]:
        """URL로 페이지 타입 감지"""
        for page_type, page_selectors in self.pages.items():
            if page_selectors.matches_url(url):
                return page_type
        return None
    
    def get_page_selectors(self, page_type: str) -> Optional[PageSelectors]:
        """특정 페이지 타입의 셀렉터 가져오기"""
        return self.pages.get(page_type)
    
    def get_selector(self, page_type: str, name: str) -> Optional[str]:
        """특정 페이지의 셀렉터 가져오기"""
        page = self.get_page_selectors(page_type)
        if page:
            return page.get_selector(name)
        return None
    
    def get_selector_by_url(self, url: str, name: str) -> Optional[str]:
        """URL 기반으로 셀렉터 자동 감지 및 반환"""
        page_type = self.detect_page_type(url)
        if page_type:
            return self.get_selector(page_type, name)
        return None


class SiteManager:
    """사이트 설정 관리자"""
    
    def __init__(self, sites_dir: Optional[str] = None):
        if sites_dir is None:
            # services/llm/sites/ -> services/ -> AI/ -> config/sites/
            sites_dir = Path(__file__).parent.parent.parent.parent / "config" / "sites"
        self.sites_dir = Path(sites_dir)
        self.sites: Dict[str, SiteConfig] = {}
        self._load_all_sites()
    
    def _load_all_sites(self) -> None:
        """모든 사이트 설정 로딩 (디렉토리 구조)"""
        if not self.sites_dir.exists():
            logger.warning(f"Sites directory not found: {self.sites_dir}")
            return
        
        for site_dir in self.sites_dir.iterdir():
            if not site_dir.is_dir():
                continue
            
            try:
                # index.json 로드
                index_file = site_dir / "index.json"
                if not index_file.exists():
                    continue
                
                with open(index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                
                site_id = index_data.get("site_id", site_dir.name)
                
                # 모든 페이지 JSON 로드
                pages: Dict[str, PageSelectors] = {}
                for page_file in site_dir.glob("*.json"):
                    if page_file.name == "index.json":
                        continue
                    try:
                        with open(page_file, "r", encoding="utf-8") as f:
                            page_data = json.load(f)
                            page_type = page_data.get("page_type")
                            if page_type:
                                pages[page_type] = PageSelectors(page_data)
                    except Exception as e:
                        logger.error(f"Failed to load page {page_file}: {e}")
                
                # SiteConfig 생성
                site = SiteConfig(site_id, index_data, pages)
                self.sites[site_id] = site
                logger.info(f"Loaded site '{site_id}' with {len(pages)} pages")
                
            except Exception as e:
                logger.error(f"Failed to load site {site_dir}: {e}")
    
    def get_site(self, site_id: str) -> Optional[SiteConfig]:
        """사이트 ID로 설정 가져오기"""
        return self.sites.get(site_id)
    
    def get_site_by_url(self, url: str) -> Optional[SiteConfig]:
        """URL로 어떤 사이트인지 판단"""
        for site in self.sites.values():
            if site.matches_domain(url):
                return site
        return None
    
    def get_site_id_by_url(self, url: str) -> Optional[str]:
        """URL로 사이트 ID 가져오기"""
        site = self.get_site_by_url(url)
        return site.site_id if site else None
    
    def get_page_type(self, url: str) -> Optional[str]:
        """URL로 페이지 타입 감지"""
        site = self.get_site_by_url(url)
        if site:
            return site.detect_page_type(url)
        return None
    
    def get_selector(self, url: str, name: str) -> Optional[str]:
        """URL 기반으로 셀렉터 자동 감지"""
        site = self.get_site_by_url(url)
        if site:
            return site.get_selector_by_url(url, name)
        return None
    
    def list_sites(self) -> List[str]:
        """등록된 모든 사이트 ID 목록"""
        return list(self.sites.keys())


# 싱글톤 인스턴스
_manager: Optional[SiteManager] = None


def get_site_manager() -> SiteManager:
    """SiteManager 싱글톤 인스턴스 반환"""
    global _manager
    if _manager is None:
        _manager = SiteManager()
    return _manager


def get_current_site(url: str) -> Optional[SiteConfig]:
    """현재 URL의 사이트 설정 반환 (편의 함수)"""
    return get_site_manager().get_site_by_url(url)


def get_selector(url: str, name: str) -> Optional[str]:
    """현재 URL 기반으로 셀렉터 자동 감지 (편의 함수)
    
    사용 예:
        selector = get_selector("https://www.coupang.com/vp/products/123", "add_to_cart")
        # -> "button.prod-cart-btn"
    """
    return get_site_manager().get_selector(url, name)


def get_page_type(url: str) -> Optional[str]:
    """URL로 페이지 타입 감지 (편의 함수)"""
    return get_site_manager().get_page_type(url)
