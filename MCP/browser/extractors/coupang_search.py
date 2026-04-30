"""
Coupang search results dynamic extraction.
"""

from typing import List, Dict, Any


async def extract_coupang_search_results(page) -> List[Dict[str, Any]]:
    """
    Extract search results with comprehensive product information on Coupang.
    """
    script = """
    () => {
      const items = Array.from(document.querySelectorAll('li[class*="ProductUnit_productUnit__"]'));
      const results = [];

      for (const item of items) {
        // Product name
        const nameEl = item.querySelector('div[class*="ProductUnit_productNameV2__"], .name');
        const name = (nameEl?.innerText || '').trim();
        if (!name) continue;

        // Price (할인가)
        const priceEl = item.querySelector('[class*="PriceArea_priceArea__"] [class*="fw-text-[20px]"], [class*="fw-text-red-700"]');
        const priceText = (priceEl?.innerText || '').trim();
        const priceMatch = priceText.match(/[\d,]+원/);
        const price = priceMatch ? priceMatch[0] : '';

        // Original price (원가)
        const originalPriceEl = item.querySelector('del');
        const originalPrice = (originalPriceEl?.innerText || '').trim();

        // Discount rate (할인율)
        const discountEl = item.querySelector('[class*="fw-bg-[#CB1400]"]');
        const discount = (discountEl?.innerText || '').trim();

        // Review count (리뷰 개수)
        const reviewEl = item.querySelector('.ProductRating_productRating__jjf7W span[class*="fw-text-[#212B36]"]');
        const reviewText = (reviewEl?.innerText || '').trim();
        const reviewMatch = reviewText.match(/\\(([0-9,]+)\\)/);
        const reviews = reviewMatch ? reviewMatch[1] : '';

        // Free shipping (무료배송)
        const freeShippingEl = item.querySelector('[class*="fw-bg-[#CCEDFD]"]');
        const freeShipping = freeShippingEl && freeShippingEl.innerText.includes('무료배송');

        // Free return (무료반품)
        const freeReturnEl = item.querySelector('[class*="fw-bg-bluegray-100"]');
        const freeReturn = freeReturnEl && freeReturnEl.innerText.includes('무료반품');

        // Delivery date (도착날짜)
        const deliveryEls = Array.from(item.querySelectorAll('span[style*="color:#008C00"]'));
        const deliveryDate = deliveryEls.map(el => el.innerText.trim()).join(' ');

        const result = {
          name,
          price,
          original_price: originalPrice,
          discount,
          reviews,
          free_shipping: freeShipping,
          free_return: freeReturn,
          delivery_date: deliveryDate
        };

        results.push(result);
      }
      return results;
    }
    """
    try:
        return await page.evaluate(script)
    except Exception:
        return []
