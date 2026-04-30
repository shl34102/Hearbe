# -*- coding: utf-8 -*-
"""
Compatibility wrapper for product info read handling.
"""

from services.llm.pipelines.read.product_info import handle_product_info_read


def handle_product_info_action(user_text, session):
    return handle_product_info_read(user_text, session)


__all__ = ["handle_product_info_action"]
