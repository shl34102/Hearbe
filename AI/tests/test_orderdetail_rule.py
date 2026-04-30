# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.llm.rules.orderdetail import OrderDetailRule


@pytest.fixture()
def rule():
    return OrderDetailRule(site_manager=None)


def test_orderdetail_rule_ignored_on_other_pages(rule, monkeypatch):
    monkeypatch.setattr("services.llm.rules.orderdetail.get_page_type", lambda _: "cart")
    result = rule.check("배송 조회", "https://cart.coupang.com/cartView.pang", None)
    assert result is None


def test_orderdetail_rule_track_delivery(rule, monkeypatch):
    monkeypatch.setattr("services.llm.rules.orderdetail.get_page_type", lambda _: "orderdetail")
    monkeypatch.setattr("services.llm.rules.orderdetail.get_selector", lambda *_: "button.track")
    result = rule.check("배송 조회", "https://mc.coupang.com/ssr/desktop/order/1", None)
    assert result is not None
    assert result.matched is True
    assert result.commands[0].tool_name == "click"
    assert result.commands[0].arguments["selector"] == "button.track"


def test_orderdetail_rule_cancel_falls_back_to_text(rule, monkeypatch):
    monkeypatch.setattr("services.llm.rules.orderdetail.get_page_type", lambda _: "orderdetail")
    monkeypatch.setattr("services.llm.rules.orderdetail.get_selector", lambda *_: None)
    result = rule.check("주문 취소", "https://mc.coupang.com/ssr/desktop/order/1", None)
    assert result is not None
    assert result.matched is True
    assert result.commands[0].tool_name == "click_text"
    assert result.commands[0].arguments["text"] == "주문 · 배송 취소"
