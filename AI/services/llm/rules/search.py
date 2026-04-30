"""
검색 규칙
"""

from typing import Optional
from . import BaseRule, RuleResult
from ..context.context_rules import (
    extract_search_query,
    detect_target_site,
    build_search_with_navigation_commands,
    build_extract_products_command,
    SITE_KEYWORDS,
)
from ..sites.site_manager import get_page_type


class SearchRule(BaseRule):
    """검색 규칙: '생수 검색', '쿠팡에서 물티슈 검색' 등"""
    
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if "검색" not in text:
            return None

        query = extract_search_query(text)
        if not query:
            return None

        # Search platform selection:
        # - If user explicitly names a platform (e.g., "쿠팡에서 ... 검색"), honor it.
        # - Otherwise, do not default to the current site blindly (e.g., Hearbe pages);
        #   for now we default to Coupang unless we're already on a searchable platform.
        explicit_site = None
        for keyword, site_id in (SITE_KEYWORDS or {}).items():
            if keyword and keyword in text:
                explicit_site = self.site_manager.get_site(site_id)
                break

        searchable_site_ids = ("coupang",)  # Expand later when other shopping sites are supported.
        if explicit_site:
            target_site = explicit_site
        elif current_site and getattr(current_site, "site_id", "") in searchable_site_ids:
            target_site = current_site
        else:
            target_site = self.site_manager.get_site("coupang")

        if not target_site:
            return None

        page_type = get_page_type(current_url) if current_url else None
        needs_navigation = True
        if current_url and target_site.matches_domain(current_url):
            # Only stay if we are already on a page that has a search bar.
            if page_type in ("main", "home", "search"):
                needs_navigation = False
        commands = build_search_with_navigation_commands(
            target_site, query, needs_navigation, current_url
        )

        extract_cmd = build_extract_products_command(target_site, current_url)
        if extract_cmd:
            commands.append(extract_cmd)

        if explicit_site:
            response_text = f"'{query}'를 {target_site.name}에서 검색합니다."
        elif current_site and getattr(current_site, "site_id", "") in searchable_site_ids:
            response_text = f"'{query}'를 {target_site.name}에서 검색합니다."
        else:
            # Current supported search platform list is effectively 1 item (Coupang).
            # Keep the phrasing as a "choice" to make future expansion easier.
            response_text = (
                "어느 플랫폼에서 검색할까요? 현재 선택 가능한 플랫폼은 1번 쿠팡입니다. "
                f"쿠팡에서 '{query}'를 검색합니다."
            )

        return RuleResult(
            matched=True,
            commands=commands,
            response_text=response_text,
            rule_name="search"
        )
