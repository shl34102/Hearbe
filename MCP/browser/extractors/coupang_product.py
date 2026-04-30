"""
Coupang product detail dynamic extraction helpers.
"""

from __future__ import annotations

from typing import Dict, Any


def _build_option_script() -> str:
    return r"""
    () => {
      const selectedOptions = {};
      const optionsList = {};
      const getText = (el) => (el && (el.innerText || el.textContent) || '').trim();
      const hasAny = (text, keywords) => keywords.some((kw) => text.includes(kw));
      const normalizeKey = (label) => {
        const text = (label || '').toLowerCase();
        if (!text) return 'option';
        if (text.includes('수량')) return 'quantity';
        if (text.includes('용량') || text.includes('중량')) return 'capacity';
        if (text.includes('사이즈') || text.includes('크기')) return 'size';
        if (text.includes('색상') || text.includes('컬러')) return 'color';
        return 'option';
      };
      const addOption = (key, option) => {
        const safeKey = key || 'option';
        if (!optionsList[safeKey]) optionsList[safeKey] = [];
        if (option && option.name) {
          optionsList[safeKey].push(option);
        }
      };
      const isSelected = (el) => {
        if (!el) return false;
        const cls = (el.className || '').toString();
        if (el.getAttribute && el.getAttribute('aria-selected') === 'true') return true;
        return (
          cls.includes('active') ||
          cls.includes('selected') ||
          cls.includes('is-selected') ||
          cls.includes('twc-border-[#346aff]') ||
          cls.includes('twc-border-[2px]')
        );
      };
      const pickFromSelect = (root) => {
        const select = root.querySelector('select');
        if (!select || select.selectedIndex < 0) return '';
        return getText(select.options[select.selectedIndex]);
      };
      const addSelectOptions = (root, key) => {
        const select = root.querySelector('select');
        if (!select) return;
        for (const opt of Array.from(select.options || [])) {
          const name = getText(opt);
          if (!name) continue;
          const selected = !!opt.selected;
          addOption(key, { name, selected });
          if (selected) {
            selectedOptions[key] = name;
          }
        }
      };
      const pickFromCustomSelect = (root) => {
        const custom = root.querySelector('.option-picker-select, .fashion-option-select, [class*="option-select"]');
        if (!custom) return '';
        const label = custom.querySelector('span[class*="flex-1"], span[class*="value"], span');
        return getText(label);
      };
      const pickFromSelectedItems = (root) => {
        const items = root.querySelectorAll(
          'li, button, div[class*="item"], span[class*="item"], div[class*="option"], div[class*="Option"]'
        );
        for (const item of items) {
          if (!isSelected(item)) continue;
          const label = getText(item);
          if (label) return label;
          const img = item.querySelector('img');
          if (img && img.alt) return img.alt.trim();
        }
        return '';
      };

      const pickFromOptionTable = (root) => {
        const selected = root.querySelector('.option-table-list__option--selected');
        if (!selected) return '';
        const name = selected.querySelector('.option-table-list__option-name');
        const text = getText(name) || getText(selected);
        return text;
      };
      const parsePrice = (priceEl) => {
        if (!priceEl) return '';
        const firstNode = priceEl.childNodes && priceEl.childNodes.length ? priceEl.childNodes[0] : null;
        let text = '';
        if (firstNode && firstNode.textContent) {
          text = firstNode.textContent;
        } else {
          text = priceEl.textContent || '';
        }
        text = text.trim();
        if (!text) return '';
        if (text.includes('원')) {
          const idx = text.indexOf('원');
          return text.slice(0, idx + 1).trim();
        }
        return text;
      };
      const parseOptionTable = (table) => {
        const label = getText(table.querySelector('.toggle-header span, .tab-selector__header-title'));
        const key = normalizeKey(label);
        const items = table.querySelectorAll('.option-table-list__option');
        for (const item of items) {
          const nameEl = item.querySelector('.option-table-list__option-name');
          const name = getText(nameEl) || getText(item);
          const priceEl = item.querySelector('.option-table-list__option-price');
          const price = parsePrice(priceEl);
          const unitPrice = getText(item.querySelector('.option-table-list__option-unit-price'));
          const selected = item.classList.contains('option-table-list__option--selected');
          addOption(key, { name, price, unit_price: unitPrice, selected });
          if (selected && name) {
            selectedOptions[key] = name;
          }
        }
      };
      const keywords = {
        size: ['사이즈', 'size', '크기'],
        color: ['색상', 'color', '컬러'],
        capacity: ['용량', 'capacity'],
        quantity: ['수량', 'quantity', '개수']
      };
      const inferKeyFromContainer = (list) => {
        const container = list.parentElement || list;
        if (!container) return 'option';
        const labels = container.querySelectorAll('label, span, div, p');
        for (const el of labels) {
          const text = getText(el);
          if (!text) continue;
          if (hasAny(text, keywords.size)) return 'size';
          if (hasAny(text, keywords.color)) return 'color';
          if (hasAny(text, keywords.capacity)) return 'capacity';
          if (hasAny(text, keywords.quantity)) return 'quantity';
        }
        return 'option';
      };
      const parseCustomScrollbars = () => {
        const lists = document.querySelectorAll('.custom-scrollbar');
        for (const list of lists) {
          const key = inferKeyFromContainer(list);
          const items = list.querySelectorAll('.select-item');
          for (const item of items) {
            const nameEl = item.querySelector('.twc-font-bold') || item.querySelector('div');
            const name = getText(nameEl) || getText(item);
            const priceEl = item.querySelector('.price-text');
            const price = parsePrice(priceEl);
            const delivery = getText(item.querySelector('.pdd-text'));
            const selected = item.classList.contains('selected');
            addOption(key, { name, price, delivery, selected });
            if (selected && name) {
              selectedOptions[key] = name;
            }
          }
        }
      };
      const tables = document.querySelectorAll('.option-table-v2');
      for (const table of tables) {
        parseOptionTable(table);
      }
      parseCustomScrollbars();
      const sections = document.querySelectorAll('section, div[class*="option"], div[class*="Option"]');
      for (const section of sections) {
        const sectionText = getText(section).toLowerCase();
        if (hasAny(sectionText, keywords.size)) {
          const key = 'size';
          addSelectOptions(section, key);
          selectedOptions.size = selectedOptions.size || pickFromOptionTable(section) || pickFromSelect(section) || pickFromCustomSelect(section) || pickFromSelectedItems(section);
        }
        if (hasAny(sectionText, keywords.color)) {
          const key = 'color';
          addSelectOptions(section, key);
          const label = section.querySelector('[class*="label-item-text"], [class*="label"] span');
          selectedOptions.color = selectedOptions.color || getText(label) || pickFromSelectedItems(section);
        }
        if (hasAny(sectionText, keywords.capacity)) {
          const key = 'capacity';
          addSelectOptions(section, key);
          selectedOptions.capacity = selectedOptions.capacity || pickFromOptionTable(section) || pickFromSelect(section) || pickFromCustomSelect(section) || pickFromSelectedItems(section);
        }
        if (hasAny(sectionText, keywords.quantity)) {
          const input = section.querySelector('input[type="number"], input[type="text"]');
          if (input && input.value) {
            selectedOptions.quantity = input.value.trim();
          } else {
            selectedOptions.quantity = selectedOptions.quantity || pickFromOptionTable(section) || pickFromSelectedItems(section);
          }
        }
      }
      if (!selectedOptions.size && !selectedOptions.color && !selectedOptions.capacity && !selectedOptions.option) {
        const fallback = document.querySelector('select[class*="option"], .option-picker-select');
        if (fallback) {
          const label = pickFromSelect(fallback) || getText(fallback);
          if (label) selectedOptions.option = label;
        }
      }
      return { selected: selectedOptions, options_list: optionsList };
    }
    """


def _build_extras_script() -> str:
    # NOTE: Coupang uses utility-like class tokens that include brackets/parentheses.
    # Using getElementsByClassName avoids CSS escaping issues for class selectors.
    return r"""
    () => {
      const getText = (el) => (el && (el.innerText || el.textContent) || '').trim();
      const uniq = (items) => {
        const out = [];
        const seen = new Set();
        for (const item of items || []) {
          const text = (item || '').trim();
          if (!text) continue;
          if (seen.has(text)) continue;
          seen.add(text);
          out.push(text);
        }
        return out;
      };

      // 1) Category breadcrumb (e.g., Home > Category > ...).
      const breadcrumbClass = 'twc-flex twc-items-center twc-pb-[16px] twc-pt-[12px]';
      const breadcrumbRaw = Array.from(document.getElementsByClassName(breadcrumbClass)).map(getText);
      let categoryPath = uniq(breadcrumbRaw);
      // On Coupang, the first breadcrumb item is typically the Home entry.
      if (categoryPath.length > 0) categoryPath = categoryPath.slice(1);

      // 2) "쿠팡 상품 정보" bullet items (key-value pairs like "용기 타입: 플라스틱병").
      const infoItemClass = 'twc-list-disc twc-list-outside twc-text-[calc(var(--adjust-font-size)+12px)]';
      const infoItems = uniq(Array.from(document.getElementsByClassName(infoItemClass)).map(getText));
      const infoKv = {};
      for (const line of infoItems) {
        const idx = line.indexOf(':');
        if (idx <= 0) continue;
        const key = line.slice(0, idx).trim();
        const value = line.slice(idx + 1).trim();
        if (!key || !value) continue;
        if (infoKv[key] === undefined) {
          infoKv[key] = value;
        }
      }

      return {
        category_path: categoryPath,
        coupang_product_info: infoItems,
        coupang_product_info_kv: infoKv,
      };
    }
    """


async def extract_coupang_product_options(page) -> Dict[str, Any]:
    """
    Extract selected option values from Coupang product pages.

    Keyword-based scan:
    - size, color, capacity, quantity
    - handles select, custom dropdown, and selected buttons
    """
    try:
        script = _build_option_script()
        return await page.evaluate(script)
    except Exception:
        return {}


async def extract_coupang_product_extras(page) -> Dict[str, Any]:
    """
    Extract additional info from Coupang product detail pages:
    - category_path: breadcrumb categories (Home removed)
    - coupang_product_info: bullet item lines
    - coupang_product_info_kv: parsed key/value pairs from bullet lines
    """
    try:
        script = _build_extras_script()
        result = await page.evaluate(script)
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}
