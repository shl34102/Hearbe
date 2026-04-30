"""
Coupang order list extraction.
"""

from __future__ import annotations

from typing import Dict, Any


async def extract_coupang_order_list(page) -> Dict[str, Any]:
    script = r"""
    () => {
      const orders = [];
      const seen = new Set();

      const getText = (el) => (el && (el.innerText || el.textContent) || '').trim();

      const pushOrder = (item) => {
        if (!item || typeof item !== 'object') return;
        const key = item.order_id || item.detail_url || `${item.title || ''}|${item.ordered_at || ''}|${item.total_price || ''}`;
        if (!key) return;
        if (seen.has(key)) return;
        seen.add(key);
        orders.push(item);
      };

      const mapOrderItem = (raw) => {
        if (!raw || typeof raw !== 'object') return null;
        const orderId = raw.orderId || raw.order_id || raw.orderNo || raw.orderNumber || raw.id || null;
        const title = raw.title || raw.productName || raw.representativeProductName || raw.productTitle || raw.name || '';
        const orderedAt = raw.orderedAt || raw.orderDate || raw.ordered_at || raw.date || '';
        const status = raw.status || raw.orderStatus || raw.deliveryStatus || raw.state || '';
        const total =
          raw.totalPrice ||
          raw.totalAmount ||
          raw.totalPayedAmount ||
          raw.totalPaidAmount ||
          raw.totalProductPrice ||
          raw.totalOrderAmount ||
          raw.totalPayment ||
          raw.totalPaymentAmount ||
          raw.totalPaymentPrice ||
          raw.totalPriceText ||
          raw.totalPriceString ||
          raw.totalPriceFormatted ||
          raw.totalPriceDisplay ||
          raw.orderAmount ||
          raw.orderPrice ||
          raw.price ||
          null;

        const normalizePrice = (value) => {
          if (value == null) return '';
          if (typeof value === 'number') return String(value);
          if (typeof value === 'string') return value.trim();
          if (typeof value === 'object') {
            const maybe = value.amount || value.value || value.price || value.text || value.display || '';
            return typeof maybe === 'string' ? maybe.trim() : (maybe != null ? String(maybe) : '');
          }
          return String(value);
        };
        const totalText = normalizePrice(total);

        const order_id = orderId ? String(orderId) : '';
        const detail_url = order_id ? `https://mc.coupang.com/ssr/desktop/order/${order_id}` : '';

        return {
          title: String(title || ''),
          ordered_at: String(orderedAt || ''),
          status: String(status || ''),
          total_price: totalText,
          detail_url,
          detail_selector: order_id ? `a[href*="/ssr/desktop/order/${order_id}"]` : '',
        };
      };

      const looksLikeOrder = (obj) => {
        if (!obj || typeof obj !== 'object') return false;
        const keys = Object.keys(obj);
        const hasId = keys.some((k) => /order(id|no|number)/i.test(k));
        const hasDate = keys.some((k) => /order(date|edAt|ed_at)/i.test(k));
        const hasStatus = keys.some((k) => /status|state|delivery/i.test(k));
        const hasTitle = keys.some((k) => /title|product|name/i.test(k));
        return (hasId && (hasDate || hasStatus || hasTitle));
      };

      const scanNode = (node) => {
        if (!node) return;
        if (Array.isArray(node)) {
          const matches = node.filter((item) => looksLikeOrder(item));
          if (matches.length >= 1) {
            for (const item of matches) {
              const mapped = mapOrderItem(item);
              if (mapped) pushOrder(mapped);
            }
          }
          for (const item of node) scanNode(item);
          return;
        }
        if (typeof node === 'object') {
          for (const value of Object.values(node)) scanNode(value);
        }
      };

      try {
        const dataEl = document.querySelector('script#__NEXT_DATA__');
        if (dataEl && dataEl.textContent) {
          const data = JSON.parse(dataEl.textContent);
          scanNode(data);
        }
      } catch (e) {
        // ignore
      }

      const pickTitle = (container) => {
        if (!container) return '';
        const link = container.querySelector('a[href*="/vp/"], a[href*="/products/"]');
        const titleEl = link || container.querySelector('[class*="title"], [class*="product"]');
        const text = getText(titleEl || container);
        if (!text) return '';
        const line = text.split('\n').map((t) => t.trim()).find((t) => t && t.length >= 2);
        return line || text;
      };

      const pickPrice = (container) => {
        if (!container) return '';
        const candidates = Array.from(container.querySelectorAll('span, em, strong'))
          .map((el) => {
            const text = getText(el);
            return { el, text };
          })
          .filter((item) => /\d[\d,]*\s*(원|₩)/.test(item.text));
        if (!candidates.length) {
          return '';
        }
        const scored = candidates.map((item) => {
          const className = (item.el.getAttribute('class') || '').toLowerCase();
          let score = 0;
          if (/price|amount|total|pay|payment/.test(className)) score += 2;
          if (/ffpsv|lgolja/.test(className)) score += 1;
          if (/총\s*결제|결제\s*금액/.test(item.text)) score += 2;
          return { ...item, score };
        });
        scored.sort((a, b) => b.score - a.score);
        const best = scored[0];
        const match = best.text.match(/(\d[\d,]*)\s*원/);
        return match ? `${match[1]}원` : best.text;
      };

      const parseContainer = (container) => {
        const text = getText(container);
        if (!text) return null;
        const orderMatch = text.match(/주문\s*번호\s*(\d+)/);
        const order_id = orderMatch ? orderMatch[1] : '';
        const dateMatch = text.match(/(20\d{2}[\.\-]\d{2}[\.\-]\d{2})/);
        const ordered_at = dateMatch ? dateMatch[1] : '';
        const statusMatch = text.match(/(배송완료|배송중|배송준비|상품준비|주문완료|결제완료|취소완료)/);
        const status = statusMatch ? statusMatch[1] : '';
        const totalMatch = text.match(/총\s*결제\s*금액\s*([\d,]+)\s*원/);
        let total_price = totalMatch ? `${totalMatch[1]}원` : '';
        if (!total_price) {
          const fallbackContainers = [
            container,
            container.parentElement,
            container.closest('article'),
            container.closest('section'),
            container.closest('li'),
          ].filter(Boolean);
          for (const node of fallbackContainers) {
            total_price = pickPrice(node);
            if (total_price) break;
          }
        }
        const title = pickTitle(container);
        const detail_url = order_id ? `https://mc.coupang.com/ssr/desktop/order/${order_id}` : '';
        const detail_selector = order_id ? `a[href*="/ssr/desktop/order/${order_id}"]` : '';

        return {
          title,
          ordered_at,
          status,
          total_price,
          detail_url,
          detail_selector,
        };
      };

      const links = Array.from(document.querySelectorAll('a[href*="/ssr/desktop/order/"]'));
      const findContainer = (link) => {
        let node = link;
        let fallback = null;
        for (let i = 0; i < 6 && node; i += 1) {
          const text = getText(node);
          if (text && /원/.test(text)) {
            fallback = node;
            if (/주문|배송|결제/.test(text)) {
              return node;
            }
          }
          node = node.parentElement;
        }
        return fallback || link.closest('li') || link.closest('div') || link.parentElement;
      };
      links.forEach((link, idx) => {
        const href = link.getAttribute('href') || '';
        const url = href.startsWith('http') ? href : `${location.origin}${href}`;
        const match = url.match(/\/ssr\/desktop\/order\/(\d+)/);
        const order_id = match ? match[1] : '';
        if (!order_id) {
          return;
        }
        let container = findContainer(link);
        let parsed = container ? parseContainer(container) : null;
        if (!parsed) {
          const price = container ? pickPrice(container) : '';
          parsed = {
            title: getText(link) || '',
            ordered_at: '',
            status: '',
            total_price: price,
            detail_url: order_id ? `https://mc.coupang.com/ssr/desktop/order/${order_id}` : url,
            detail_selector: order_id ? `a[href*="/ssr/desktop/order/${order_id}"]` : `a[href*="/ssr/desktop/order/"]:nth-of-type(${idx + 1})`,
          };
        } else {
          parsed.detail_url = parsed.detail_url || (order_id ? `https://mc.coupang.com/ssr/desktop/order/${order_id}` : url);
          if (!parsed.detail_selector) {
            parsed.detail_selector = order_id ? `a[href*="/ssr/desktop/order/${order_id}"]` : `a[href*="/ssr/desktop/order/"]:nth-of-type(${idx + 1})`;
          }
        }
        pushOrder(parsed);
      });

      // Keep only real order-detail entries. This prevents "마이쿠팡" / list links from
      // being treated as an order (which breaks "N번째 주문 상세보기" indexing).
      // Some order detail links include query strings or trailing slashes.
      // Accept those so we don't drop all orders and break "N번째 주문 상세보기".
      const isOrderDetailUrl = (url) => /\/ssr\/desktop\/order\/\d+(?:[/?#].*)?$/.test(String(url || ''));
      const filtered = orders.filter((o) => isOrderDetailUrl(o && o.detail_url));

      filtered.forEach((item, idx) => { item.index = idx + 1; });

      return {
        orders: filtered,
        count: filtered.length,
      };
    }
    """

    try:
        result = await page.evaluate(script)
        if not isinstance(result, dict):
            return {"orders": [], "count": 0}
        return result
    except Exception:
        return {"orders": [], "count": 0}
