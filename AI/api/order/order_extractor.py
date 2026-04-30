# -*- coding: utf-8 -*-
"""
Coupang order page HTML extractor.

Parses order history from Coupang order list page.
URL: https://mc.coupang.com/ssr/desktop/order/list
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = Any  # type: ignore
    HAS_BS4 = False

try:
    from .order_client import OrderItem
except ImportError:
    from order_client import OrderItem

logger = logging.getLogger(__name__)


@dataclass
class ExtractedOrder:
    """Extracted order from Coupang page."""
    order_date: Optional[str] = None
    items: List[OrderItem] = field(default_factory=list)
    order_url: Optional[str] = None


class OrderExtractor:
    """
    Extracts order items from Coupang order history page HTML.

    Coupang order page structure (typical):
    - Order groups by date
    - Each order contains product items
    - Each item has: name, price, quantity, image, product URL, delivery tracking URL
    """

    COUPANG_ORDER_URL = "https://mc.coupang.com/ssr/desktop/order/list"

    def __init__(self):
        if not HAS_BS4:
            raise ImportError("BeautifulSoup4 required: pip install beautifulsoup4")

    def extract_from_html(self, html: str) -> List[ExtractedOrder]:
        """
        Extract orders from Coupang order history HTML.

        Args:
            html: Raw HTML content from order list page

        Returns:
            List of ExtractedOrder with items
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        orders = []

        # Try multiple selectors for order containers
        order_containers = self._find_order_containers(soup)

        for container in order_containers:
            order = self._parse_order_container(container)
            if order and order.items:
                orders.append(order)

        logger.info("Extracted %d orders with %d total items",
                    len(orders),
                    sum(len(o.items) for o in orders))
        return orders

    def _find_order_containers(self, soup: BeautifulSoup) -> List[Any]:
        """Find order container elements using multiple selectors."""
        # Common Coupang order container selectors
        selectors = [
            "div.order-list-item",
            "div.order-item",
            "div[class*='order']",
            "section.order-section",
            "div.my-order-item",
            "li.order-item",
        ]

        for selector in selectors:
            containers = soup.select(selector)
            if containers:
                logger.debug("Found %d order containers with selector: %s",
                            len(containers), selector)
                return containers

        # Fallback: look for product items directly
        product_selectors = [
            "div.product-item",
            "div[class*='product']",
            "div.item-info",
        ]
        for selector in product_selectors:
            items = soup.select(selector)
            if items:
                logger.debug("Found %d product items with selector: %s",
                            len(items), selector)
                # Wrap each item as a separate order
                return items

        return []

    def _parse_order_container(self, container) -> Optional[ExtractedOrder]:
        """Parse a single order container element."""
        order = ExtractedOrder()

        # Extract order date
        date_selectors = [
            "span.order-date",
            "div.date",
            "span[class*='date']",
            "time",
        ]
        for selector in date_selectors:
            date_elem = container.select_one(selector)
            if date_elem:
                order.order_date = self._clean_text(date_elem.get_text())
                break

        # Extract order detail URL
        link_selectors = [
            "a.order-detail-link",
            "a[href*='order']",
            "a[href*='detail']",
        ]
        for selector in link_selectors:
            link = container.select_one(selector)
            if link and link.get("href"):
                order.order_url = self._normalize_url(link.get("href"))
                break

        # Extract product items
        item_selectors = [
            "div.product-item",
            "div.item-info",
            "li.product",
            "div[class*='product']",
            "tr.product-row",
        ]

        for selector in item_selectors:
            items = container.select(selector)
            if items:
                for item_elem in items:
                    order_item = self._parse_product_item(item_elem)
                    if order_item:
                        order.items.append(order_item)
                break

        # If no nested items found, try to parse container itself as a product
        if not order.items:
            order_item = self._parse_product_item(container)
            if order_item:
                order.items.append(order_item)

        return order if order.items else None

    def _parse_product_item(self, elem) -> Optional[OrderItem]:
        """Parse a single product item element."""
        name = self._extract_name(elem)
        if not name:
            return None

        price = self._extract_price(elem)
        quantity = self._extract_quantity(elem)
        img_url = self._extract_image_url(elem)
        product_url = self._extract_product_url(elem)
        deliver_url = self._extract_delivery_url(elem)

        return OrderItem(
            name=name,
            price=price,
            quantity=quantity,
            url=product_url,
            img_url=img_url,
            deliver_url=deliver_url,
        )

    def _extract_name(self, elem) -> Optional[str]:
        """Extract product name from element."""
        name_selectors = [
            "a.product-name",
            "span.product-name",
            "div.product-name",
            "a[class*='name']",
            "span[class*='name']",
            "div[class*='title']",
            "a.prod-name",
            "span.prod-name",
        ]
        for selector in name_selectors:
            name_elem = elem.select_one(selector)
            if name_elem:
                return self._clean_text(name_elem.get_text())

        # Fallback: first <a> with href containing product
        links = elem.select("a[href*='product']")
        for link in links:
            text = self._clean_text(link.get_text())
            if text and len(text) > 5:
                return text

        return None

    def _extract_price(self, elem) -> int:
        """Extract price from element."""
        price_selectors = [
            "span.price",
            "div.price",
            "span[class*='price']",
            "em.price",
            "strong.price",
        ]
        for selector in price_selectors:
            price_elem = elem.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text()
                return self._parse_price(price_text)

        # Fallback: look for Korean won pattern in text
        text = elem.get_text()
        match = re.search(r"(\d{1,3}(?:,\d{3})*)\s*원", text)
        if match:
            return self._parse_price(match.group(1))

        return 0

    def _parse_price(self, price_text: str) -> int:
        """Parse price string to integer."""
        if not price_text:
            return 0
        # Remove commas, spaces, and non-digit characters
        digits = re.sub(r"[^\d]", "", price_text)
        try:
            return int(digits)
        except ValueError:
            return 0

    def _extract_quantity(self, elem) -> int:
        """Extract quantity from element."""
        qty_selectors = [
            "span.quantity",
            "span[class*='count']",
            "span[class*='qty']",
            "div.quantity",
        ]
        for selector in qty_selectors:
            qty_elem = elem.select_one(selector)
            if qty_elem:
                qty_text = qty_elem.get_text()
                match = re.search(r"(\d+)", qty_text)
                if match:
                    return int(match.group(1))

        # Fallback: look for "수량: N" or "N개" pattern
        text = elem.get_text()
        patterns = [
            r"수량[:\s]*(\d+)",
            r"(\d+)\s*개",
            r"x\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))

        return 1  # Default quantity

    def _extract_image_url(self, elem) -> Optional[str]:
        """Extract product image URL."""
        img = elem.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                return self._normalize_url(src)
        return None

    def _extract_product_url(self, elem) -> Optional[str]:
        """Extract product detail URL."""
        link_selectors = [
            "a.product-name",
            "a[href*='product']",
            "a[href*='vp/products']",
            "a.prod-name",
        ]
        for selector in link_selectors:
            link = elem.select_one(selector)
            if link and link.get("href"):
                return self._normalize_url(link.get("href"))
        return None

    def _extract_delivery_url(self, elem) -> Optional[str]:
        """Extract delivery tracking URL."""
        link_selectors = [
            "a[href*='delivery']",
            "a[href*='tracking']",
            "a[href*='ship']",
            "a.delivery-tracking",
        ]
        for selector in link_selectors:
            link = elem.select_one(selector)
            if link and link.get("href"):
                return self._normalize_url(link.get("href"))
        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        # Remove excessive whitespace
        return " ".join(text.split()).strip()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to absolute form."""
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return "https://www.coupang.com" + url
        return url


def extract_orders_from_page_data(page_data: Dict[str, Any]) -> List[OrderItem]:
    """
    Extract order items from MCP page_data response.

    This is a convenience function for integration with MCP handler.

    Args:
        page_data: MCP result containing HTML or structured order data

    Returns:
        List of OrderItem ready for backend API
    """
    # Check for pre-parsed order data
    if "orders" in page_data:
        items = []
        for order in page_data["orders"]:
            for item in order.get("items", []):
                items.append(OrderItem(
                    name=item.get("name", ""),
                    price=item.get("price", 0),
                    quantity=item.get("quantity", 1),
                    url=item.get("url"),
                    img_url=item.get("img_url") or item.get("imgUrl"),
                    deliver_url=item.get("deliver_url") or item.get("deliverUrl"),
                    coupang_product_number=(
                        item.get("coupang_product_number")
                        or item.get("coupangProductNumber")
                    ),
                    category_path=item.get("category_path") or item.get("categoryPath"),
                ))
        return items

    # Try HTML extraction
    html = page_data.get("html")
    if html:
        extractor = OrderExtractor()
        orders = extractor.extract_from_html(html)
        items = []
        for order in orders:
            items.extend(order.items)
        return items

    return []
