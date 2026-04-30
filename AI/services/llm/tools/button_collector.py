"""
Button Collector Module
Collects clickable elements from a web page using Playwright
"""

# JavaScript code for collecting buttons
BUTTON_COLLECTOR_JS = """
() => {
    const results = [];

    // Button elements
    document.querySelectorAll('button').forEach((el, i) => {
        if (el.offsetParent !== null) {
            results.push({
                type: 'button',
                text: el.innerText.trim().substring(0, 50),
                selector: el.id ? '#' + el.id : (el.className ? 'button.' + el.className.split(' ')[0] : 'button:nth-of-type(' + (i+1) + ')'),
                visible: true
            });
        }
    });

    // input[type=submit], input[type=button]
    document.querySelectorAll('input[type="submit"], input[type="button"]').forEach((el, i) => {
        if (el.offsetParent !== null) {
            results.push({
                type: 'input-button',
                text: el.value || el.placeholder || '',
                selector: el.id ? '#' + el.id : 'input[type="' + el.type + '"]:nth-of-type(' + (i+1) + ')',
                visible: true
            });
        }
    });

    // Input fields (text, email, password, tel, search)
    document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], input[type="tel"], input[type="search"], input:not([type])').forEach((el, i) => {
        if (el.offsetParent !== null) {
            results.push({
                type: 'input-field',
                text: el.placeholder || el.name || el.id || '',
                selector: el.id ? '#' + el.id : (el.name ? 'input[name="' + el.name + '"]' : 'input[type="' + (el.type || 'text') + '"]:nth-of-type(' + (i+1) + ')'),
                visible: true
            });
        }
    });

    // Navigation links (a tags with id or title)
    document.querySelectorAll('a[id], a[title], a.nav-link, a.menu-link, header a, nav a').forEach((el, i) => {
        if (el.offsetParent !== null && el.innerText.trim()) {
            const exists = results.some(r => r.text === el.innerText.trim().substring(0, 50));
            if (!exists) {
                results.push({
                    type: 'nav-link',
                    text: el.innerText.trim().substring(0, 50),
                    selector: el.id ? '#' + el.id : (el.title ? 'a[title="' + el.title + '"]' : null),
                    visible: true
                });
            }
        }
    });

    // Checkboxes
    document.querySelectorAll('input[type="checkbox"], label[role="checkbox"]').forEach((el, i) => {
        if (el.offsetParent !== null) {
            var text = '';
            if (el.tagName === 'LABEL') {
                text = el.getAttribute('aria-label') || el.innerText.trim();
            } else {
                var sibling = el.nextElementSibling;
                var parent = el.parentElement;
                text = (sibling ? sibling.innerText : '') || (parent ? parent.innerText : '') || '';
                text = text.trim();
            }
            results.push({
                type: 'checkbox',
                text: text.substring(0, 50),
                selector: el.id ? '#' + el.id : (el.getAttribute('for') ? 'label[for="' + el.getAttribute('for') + '"]' : null),
                visible: true
            });
        }
    });

    // Link buttons (role=button or btn class)
    document.querySelectorAll('a[role="button"], a.btn, a.button, [role="button"]').forEach((el, i) => {
        if (el.offsetParent !== null && el.innerText.trim()) {
            results.push({
                type: 'link-button',
                text: el.innerText.trim().substring(0, 50),
                selector: el.id ? '#' + el.id : null,
                visible: true
            });
        }
    });

    // Tab links (a tags with data-tab attribute)
    document.querySelectorAll('a[data-tab], a[data-id], [role="tab"]').forEach((el, i) => {
        if (el.offsetParent !== null && el.innerText.trim()) {
            const exists = results.some(r => r.text === el.innerText.trim().substring(0, 50));
            if (!exists) {
                var tabValue = el.dataset ? (el.dataset.tab || '') : '';
                results.push({
                    type: 'tab',
                    text: el.innerText.trim().substring(0, 50),
                    selector: el.className ? 'a.' + el.className.split(' ')[0] + '[data-tab="' + tabValue + '"]' : 'a[data-tab="' + tabValue + '"]',
                    visible: true
                });
            }
        }
    });

    // Shopping action elements (cart, buy, checkout)
    var shoppingSelectors = [
        '.prod-buy-btn', '.add-cart', '.buy-btn', '.cart-btn',
        '[class*="purchase"]', '[class*="buy"]', '[class*="cart"]',
        '[class*="order"]', '[class*="checkout"]'
    ];
    shoppingSelectors.forEach(function(sel) {
        document.querySelectorAll(sel).forEach(function(el) {
            if (el.offsetParent !== null && el.innerText.trim()) {
                var exists = results.some(function(r) { return r.text === el.innerText.trim().substring(0, 50); });
                if (!exists) {
                    results.push({
                        type: 'shopping-action',
                        text: el.innerText.trim().substring(0, 50),
                        selector: sel,
                        visible: true
                    });
                }
            }
        });
    });

    return results.slice(0, 30);
}
"""


async def collect_buttons(page):
    """
    Collect clickable elements from a page

    Args:
        page: Playwright page object

    Returns:
        dict: {"success": bool, "buttons": list, "count": int, "error": str (optional)}
    """
    if not page:
        return {"success": False, "error": "Page not available", "buttons": []}

    try:
        elements = await page.evaluate(BUTTON_COLLECTOR_JS)
        return {"success": True, "buttons": elements, "count": len(elements)}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}", "buttons": []}
