"""
Coupang cart dynamic extraction.
"""

from __future__ import annotations

from typing import Dict, Any


async def extract_coupang_cart(page) -> Dict[str, Any]:
    script = r"""
    () => {
      const items = [];
      const getText = (el) => (el && (el.innerText || el.textContent) || '').trim();
      const parseNumber = (text) => {
        if (!text) return null;
        const cleaned = String(text).replace(/,/g, '');
        const match = cleaned.match(/\d+/);
        if (!match) return null;
        return parseInt(match[0], 10);
      };
      const formatPrice = (num) => {
        if (num === null || Number.isNaN(num)) return '';
        return `${num.toLocaleString('ko-KR')}원`;
      };
      const parsePrice = (text) => formatPrice(parseNumber(text));
      const extractNumbers = (text) => {
        if (!text) return [];
        const cleaned = String(text).replace(/,/g, '');
        const matches = cleaned.match(/\d+/g) || [];
        return matches
          .map((value) => parseInt(value, 10))
          .filter((value) => !Number.isNaN(value));
      };
      const pickPriceFrom = (root) => {
        // Avoid invalid selector errors for utility class names like twc-text-[20px]
        const selectors = [
          '[data-id="sale-price-ccid"]',
          '.price',
          '[class~="twc-text-[20px]"]',
          '[class*="twc-text-[20px]"]',
        ];
        let priceEl = null;
        for (const sel of selectors) {
          priceEl = root.querySelector(sel);
          if (priceEl) break;
        }
        if (!priceEl) return '';
        return parsePrice(getText(priceEl));
      };
      const pickArrival = (root) => {
        const parts = [];
        const txt = root.querySelector('#arrive-date-txt');
        const day = root.querySelector('#arrive-date-day');
        const date = root.querySelector('#arrive-date-date');
        const time = root.querySelector('#arrive-date-time');
        const promise = root.querySelector('#promise-txt');
        if (txt) parts.push(getText(txt));
        if (day) parts.push(getText(day));
        if (date) parts.push(getText(date));
        if (time) parts.push(getText(time));
        if (promise) parts.push(getText(promise));
        return parts.join(' ').trim();
      };
      const bundleSelectors = [
        '#mainContent [id^="item_"]',
        '#mainContent .cart-product',
        '.cart-product-list [id^="item_"]',
        '.cart-product-list .cart-product',
        '[id^="item_"]',
        '.cart-product',
      ];
      const bundleSet = new Set();
      for (const sel of bundleSelectors) {
        document.querySelectorAll(sel).forEach((el) => bundleSet.add(el));
      }
      const bundles = Array.from(bundleSet);
      for (const item of bundles) {
        const checkbox = item.querySelector('input[type="checkbox"]');

        const nameEl = item.querySelector('a span.twc-text-custom-black')
          || item.querySelector('#name span.twc-text-custom-black')
          || item.querySelector('#name span')
          || item.querySelector('.product-name')
          || item.querySelector('span.twc-text-custom-black')
          || item.querySelector('a span');
        let name = getText(nameEl);
        if (!name && checkbox) {
          name = (checkbox.getAttribute('title') || '').trim();
        }

        const optionEl = item.querySelector('span.twc-text-custom-637381')
          || item.querySelector('#name span.twc-text-custom-637381')
          || item.querySelector('.product-option');
        let option = getText(optionEl);
        if (option) {
          option = option.replace('옵션', '').replace(':', '').trim();
        }

        const price = pickPriceFrom(item);
        const arrival = pickArrival(item);
        const qtyInput = item.querySelector('input.cart-quantity-input')
          || item.querySelector('input[type="number"]')
          || item.querySelector('input[type="text"]');
        const quantity = qtyInput ? qtyInput.value : '';
        const selectedAttr = item.getAttribute('data-selected');
        const selected = (selectedAttr === 'true') || (checkbox ? checkbox.checked === true : false);

        if (name) {
          items.push({
            name,
            option,
            arrival,
            price,
            quantity,
            selected,
          });
        }
      }

      const findRocketFreshRoot = () => {
        const links = Array.from(document.querySelectorAll('a'));
        for (const link of links) {
          const text = getText(link);
          if (!text.includes('로켓프레시 상품 추가하기')) {
            continue;
          }
          let node = link.parentElement;
          while (node) {
            const nodeText = getText(node);
            if (nodeText.includes('로켓프레시 상품') && nodeText.includes('이상 추가 시')) {
              return node;
            }
            node = node.parentElement;
          }
        }

        const blocks = Array.from(document.querySelectorAll('div'));
        for (const block of blocks) {
          const text = getText(block);
          if (text.includes('로켓프레시 상품') && text.includes('이상 추가 시')) {
            return block;
          }
        }
        return null;
      };

      const extractRocketFreshInfo = () => {
        const root = findRocketFreshRoot();
        if (!root) return null;

        const progress = root.querySelector('.threshold-popup-progressbar');
        if (!progress) return null;

        const ems = Array.from(root.querySelectorAll('em'));
        let current = null;
        for (const em of ems) {
          const value = parseNumber(getText(em));
          if (value !== null) {
            current = value;
            break;
          }
        }

        const numbers = extractNumbers(getText(root));
        const progressNumbers = extractNumbers(getText(progress));
        let threshold = null;
        if (progressNumbers.length) {
          threshold = Math.max(...progressNumbers);
        }
        if (numbers.length >= 2) {
          const min = Math.min(...numbers);
          const max = Math.max(...numbers);
          if (current === null) {
            current = min;
          }
          if (threshold === null) {
            threshold = max;
          }
        } else if (numbers.length === 1 && current === null) {
          current = numbers[0];
        }

        let addUrl = '';
        const addLink = Array.from(root.querySelectorAll('a'))
          .find((el) => getText(el).includes('로켓프레시 상품 추가하기'));
        if (addLink) {
          addUrl = addLink.getAttribute('href') || '';
          if (addUrl.startsWith('//')) {
            addUrl = `https:${addUrl}`;
          } else if (addUrl.startsWith('/')) {
            addUrl = `https://www.coupang.com${addUrl}`;
          }
        }

        let remaining = null;
        if (current !== null && threshold !== null) {
          remaining = Math.max(threshold - current, 0);
        }

        return {
          current,
          threshold,
          remaining,
          addUrl,
        };
      };

      const summary = {};
      const setSummary = (key, value) => {
        if (value && !summary[key]) {
          summary[key] = value;
        }
      };
      const totalAreas = document.querySelectorAll('[data-component-id="total-price"]');
      totalAreas.forEach((totalArea) => {
        const rows = totalArea.querySelectorAll('div.twc-flex.twc-justify-between');
        for (const row of rows) {
          const text = getText(row);
          if (!text) continue;
          const normalized = text.replace(/\s+/g, '');
          if (normalized.includes('총상품가격')) {
            const val = row.querySelector('em[translate="no"]')
              || row.querySelector('em.final-product-price')
              || row.querySelector('em');
            setSummary('total_product_price', parsePrice(getText(val)));
          }
          if (normalized.includes('총즉시할인')) {
            const val = row.querySelector('em[translate="no"]') || row.querySelector('em');
            setSummary('total_instant_discount', parsePrice(getText(val)));
          }
          if (normalized.includes('총배송비')) {
            const val = row.querySelector('em[translate="no"]')
              || row.querySelector('em.final-product-price')
              || row.querySelector('em');
            setSummary('shipping_fee', parsePrice(getText(val)));
          }
        }
      });

      const finalOrder = document.querySelector('#finalOrderPrice');
      if (finalOrder) {
        const val = finalOrder.querySelector('em[translate="no"]')
          || finalOrder.querySelector('em')
          || finalOrder;
        const total = parsePrice(getText(val));
        if (total) {
          summary.total_price = total;
          summary.final_order_price = total;
        }
      } else {
        const finalAttr = document.querySelector('[data-final-order-price]');
        if (finalAttr) {
          const total = parsePrice(finalAttr.getAttribute('data-final-order-price') || '');
          if (total) {
            summary.total_price = total;
            summary.final_order_price = total;
          }
        }
      }

      const rocketFresh = extractRocketFreshInfo();
      if (rocketFresh) {
        if (rocketFresh.current !== null) {
          summary.rocket_fresh_current = formatPrice(rocketFresh.current);
        }
        if (rocketFresh.threshold !== null) {
          summary.rocket_fresh_threshold = formatPrice(rocketFresh.threshold);
        }
        if (rocketFresh.remaining !== null) {
          summary.rocket_fresh_remaining = formatPrice(rocketFresh.remaining);
        }
        if (rocketFresh.remaining !== null && rocketFresh.remaining > 0) {
          summary.rocket_fresh_blocked = true;
        }
        if (rocketFresh.addUrl) {
          summary.rocket_fresh_add_url = rocketFresh.addUrl;
        }
      }

      const isCartPage = (
        window.location.href.includes('cartView')
        || document.querySelector('[data-component-id="total-price"]')
        || document.querySelector('.cart-product')
        || document.querySelector('[id^="item_"]')
      );

      return { items, summary, is_cart_page: Boolean(isCartPage) };
    }
    """

    try:
        result = await page.evaluate(script)
        if not isinstance(result, dict):
            return {"items": [], "summary": {}}
        return result
    except Exception:
        return {"items": [], "summary": {}}
