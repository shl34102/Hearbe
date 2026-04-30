# 상품 페이지 이미지 URL 수집·다운로드
import os
import re
import hashlib
import tempfile
from pathlib import Path
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests


SITE_CONFIGS: Dict[str, Dict] = {
    "coupang": {
        "name": "쿠팡",
        "selector": ".product-detail-content-inside img",
        "exclude_patterns": [
            r"/banner/", r"/ad/", r"/icon/", r"/logo/",
            r"/button/", r"/badge/", r"static\.coupang",
            r"ads\.", r"pixel\.", r"/event/", r"/promotion/",
        ],
        "include_patterns": [
            r"/vendor-item/", r"/product/", r"/thumbnail",
            r"/remote/", r"thumbnail\d*\.coupangcdn\.com",
        ],
    },
    "naver": {
        "name": "네이버",
        "selector": "#INTRODUCE img",
        "exclude_patterns": [
            r"/ad/", r"/banner/", r"/static/", r"/icon/",
            r"/logo/", r"adimg\.", r"ssl\.pstatic\.net/static",
        ],
        "include_patterns": [
            r"/shop/", r"/product/", r"/smartstore/",
            r"shop-phinf\.pstatic\.net", r"shopping-phinf\.pstatic\.net",
        ],
    },
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024  # 이미지 1장당 최대 다운로드 크기 20MB

# 내부/비공개 네트워크 접근 차단 (SSRF 방어)
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
_BLOCKED_IP_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                        "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                        "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                        "172.30.", "172.31.", "192.168.", "169.254.")


def _is_safe_url(url: str) -> bool:
    """내부 네트워크 URL 차단"""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname in _BLOCKED_HOSTS:
        return False
    if hostname.startswith(_BLOCKED_IP_PREFIXES):
        return False
    return True


def detect_site(url: str) -> Optional[str]:
    url_lower = url.lower()
    
    if "coupang" in url_lower:
        return "coupang"
    elif "naver" in url_lower or "pstatic.net" in url_lower:
        return "naver"
    
    return None


def _matches_pattern(url: str, patterns: List[str]) -> bool:
    url_lower = url.lower()
    return any(re.search(pattern, url_lower) for pattern in patterns)


def _is_valid_image_url(url: str) -> bool:
    if not url or not url.startswith(("http://", "https://")):
        return False

    if not _is_safe_url(url):
        return False

    parsed = urlparse(url)
    path_lower = parsed.path.lower()

    _, ext = os.path.splitext(path_lower)
    if ext:
        # 명백한 비이미지 확장자는 제외
        if ext in {".html", ".htm", ".js", ".css"}:
            return False
        # 확장자가 있지만 이미지가 아닌 경우도 CDN URL일 수 있으므로 통과
        # (최종 검증은 download_image에서 Content-Type으로 수행)

    return True


def filter_product_images(
    image_urls: List[str],
    site: str = "auto"
) -> List[str]:
    if not image_urls:
        return []
    
    filtered = []
    seen = set()
    
    for url in image_urls:
        if url in seen:
            continue
        seen.add(url)
        
        if not _is_valid_image_url(url):
            continue
        
        current_site = site if site != "auto" else detect_site(url)
        
        if current_site and current_site in SITE_CONFIGS:
            config = SITE_CONFIGS[current_site]
            
            if _matches_pattern(url, config["exclude_patterns"]):
                continue
            
            if _matches_pattern(url, config["include_patterns"]):
                filtered.append(url)
                continue
        
        filtered.append(url)
    
    return filtered


def _generate_filename(url: str) -> str:
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    
    parsed = urlparse(url)
    path = parsed.path
    _, ext = os.path.splitext(path)
    
    if not ext or ext.lower() not in SUPPORTED_EXTENSIONS:
        ext = ".jpg"
    
    return f"img_{url_hash}{ext}"


def download_image(
    url: str,
    save_dir: str = None,
    timeout: int = 30
) -> Optional[str]:
    if save_dir is None:
        save_dir = tempfile.mkdtemp(prefix="ocr_images_")
    
    os.makedirs(save_dir, exist_ok=True)
    
    filename = _generate_filename(url)
    local_path = os.path.join(save_dir, filename)
    
    if os.path.exists(local_path):
        return local_path
    
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": url,
        }
        
        response = requests.get(
            url, headers=headers, timeout=timeout,
            stream=True, allow_redirects=False,
        )

        # 리다이렉트 시 대상 URL의 안전성 재검증 (SSRF 방어)
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("Location", "")
            if not redirect_url or not _is_safe_url(redirect_url):
                return None
            response = requests.get(
                redirect_url, headers=headers, timeout=timeout,
                stream=True, allow_redirects=False,
            )

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return None

        downloaded = 0
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_SIZE:
                    break
                f.write(chunk)

        if downloaded > MAX_DOWNLOAD_SIZE:
            os.remove(local_path)
            return None

        return local_path

    except requests.RequestException:
        if os.path.exists(local_path):
            os.remove(local_path)
        return None


def download_images(
    urls: List[str],
    save_dir: str = None,
    max_workers: int = 4,
    timeout: int = 30
) -> List[str]:
    if not urls:
        return []

    if save_dir is None:
        save_dir = tempfile.mkdtemp(prefix="ocr_images_")

    os.makedirs(save_dir, exist_ok=True)

    # 입력 순서를 보존하기 위해 인덱스 기반 결과 수집
    url_to_idx = {url: i for i, url in enumerate(urls)}
    results = [None] * len(urls)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(download_image, url, save_dir, timeout): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                local_path = future.result()
                if local_path:
                    results[url_to_idx[url]] = local_path
            except Exception:
                pass

    # None 제거하여 성공한 경로만 반환 (입력 순서 유지)
    return [p for p in results if p is not None]


def get_site_config(site: str) -> Optional[Dict]:
    return SITE_CONFIGS.get(site)


def get_selector(site: str) -> Optional[str]:
    config = SITE_CONFIGS.get(site)
    return config["selector"] if config else None


def list_supported_sites() -> List[str]:
    return list(SITE_CONFIGS.keys())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="이미지 URL 필터링 및 다운로드")
    parser.add_argument("--urls", nargs="+")
    parser.add_argument("--site", default="auto", choices=["auto", "coupang", "naver"])
    parser.add_argument("--output", default="downloaded_images")
    parser.add_argument("--filter-only", action="store_true")
    args = parser.parse_args()
    
    if not args.urls:
        print("사용법: python image_fetcher.py --urls URL1 URL2 ...")
        print("\n지원 사이트:")
        for site, config in SITE_CONFIGS.items():
            print(f"  - {site}: {config['name']} ({config['selector']})")
        exit(1)
    
    print(f"\n🔍 이미지 필터링 (사이트: {args.site})")
    filtered = filter_product_images(args.urls, site=args.site)
    print(f"  → {len(args.urls)}개 → {len(filtered)}개")
    
    if args.filter_only:
        print("\n필터링된 URL:")
        for url in filtered:
            print(f"  - {url}")
    else:
        local_paths = download_images(filtered, save_dir=args.output)
        print(f"\n저장 위치: {args.output}/")
