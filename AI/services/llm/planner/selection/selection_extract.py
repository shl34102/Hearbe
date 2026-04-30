"""
Helpers for building follow-up extract commands after selection.
"""

from typing import Optional

from core.interfaces import MCPCommand, SessionState
from ...sites.site_manager import get_site_manager, get_current_site
from .site_extractors import build_product_extract_command_for_site


def build_product_extract_command(
    session: Optional[SessionState],
) -> Optional[MCPCommand]:
    if not session:
        return None

    current_url = session.current_url or ""
    site = None
    if session.current_site:
        site = get_site_manager().get_site(session.current_site)
    if not site and current_url:
        site = get_current_site(current_url)

    return build_product_extract_command_for_site(site, current_url=current_url)
