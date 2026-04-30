# -*- coding: utf-8 -*-
"""Read-only pipelines."""

from .product_info import handle_product_info_read
from .page_info import handle_page_info_read
from .cart_summary import handle_cart_summary_read
from .order_list_summary import handle_order_list_summary_read
from .search_summary import handle_search_summary_read

__all__ = [
    "handle_product_info_read",
    "handle_page_info_read",
    "handle_cart_summary_read",
    "handle_order_list_summary_read",
    "handle_search_summary_read",
]
