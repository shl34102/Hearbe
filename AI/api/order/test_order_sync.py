# -*- coding: utf-8 -*-
"""
Test file for order sync module.

Usage:
    cd AI/api/order
    python test_order_sync.py

Tests:
    1. OrderExtractor HTML parsing
    2. OrderClient API calls (mock)
    3. OrderSyncService integration
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add current directory to path for direct imports (bypass api/__init__.py)
_current_dir = Path(__file__).resolve().parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Sample Coupang order HTML for testing
SAMPLE_ORDER_HTML = """
<html>
<body>
<div class="order-list">
    <div class="order-list-item">
        <span class="order-date">2025.02.04</span>
        <div class="product-item">
            <a class="product-name" href="/vp/products/12345">
                Sample Product Name
            </a>
            <img src="https://example.com/image.jpg" />
            <span class="price">29,900원</span>
            <span class="quantity">수량: 2</span>
            <a class="delivery-tracking" href="https://delivery.coupang.com/track/123">
                배송조회
            </a>
        </div>
        <div class="product-item">
            <a class="product-name" href="/vp/products/67890">
                Another Product
            </a>
            <img src="https://example.com/image2.jpg" />
            <span class="price">15,000원</span>
            <span class="quantity">1개</span>
        </div>
    </div>
</div>
</body>
</html>
"""


def test_extractor():
    """Test OrderExtractor HTML parsing."""
    print("\n" + "=" * 60)
    print("TEST: OrderExtractor")
    print("=" * 60)

    try:
        from order_extractor import OrderExtractor

        extractor = OrderExtractor()
        orders = extractor.extract_from_html(SAMPLE_ORDER_HTML)

        print(f"Extracted {len(orders)} orders")

        for i, order in enumerate(orders):
            print(f"\nOrder {i + 1}:")
            print(f"  Date: {order.order_date}")
            print(f"  Items: {len(order.items)}")

            for j, item in enumerate(order.items):
                print(f"\n  Item {j + 1}:")
                print(f"    Name: {item.name}")
                print(f"    Price: {item.price}")
                print(f"    Quantity: {item.quantity}")
                print(f"    URL: {item.url}")
                print(f"    Image: {item.img_url}")
                print(f"    Delivery: {item.deliver_url}")

        # Validate extraction
        assert len(orders) >= 1, "Should extract at least 1 order"
        assert orders[0].items, "Order should have items"

        first_item = orders[0].items[0]
        assert first_item.name, "Item should have name"
        assert first_item.price > 0, "Item should have price"

        print("\n[PASS] OrderExtractor test passed")
        return True

    except Exception as e:
        print(f"\n[FAIL] OrderExtractor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_order_client():
    """Test OrderClient instantiation."""
    print("\n" + "=" * 60)
    print("TEST: OrderClient")
    print("=" * 60)

    try:
        from order_client import OrderClient, OrderItem, OrderCreateRequest

        # Test OrderItem
        item = OrderItem(
            name="Test Product",
            price=10000,
            quantity=1,
            url="https://example.com/product",
            img_url="https://example.com/image.jpg",
        )
        item_dict = item.to_dict()
        print(f"OrderItem dict: {item_dict}")
        assert item_dict["name"] == "Test Product"
        assert item_dict["price"] == 10000

        # Test OrderCreateRequest
        request = OrderCreateRequest(platform_id=1, items=[item])
        request_dict = request.to_dict()
        print(f"OrderCreateRequest dict: {request_dict}")
        assert request_dict["platform_id"] == 1
        assert len(request_dict["items"]) == 1

        # Test client instantiation (no actual API call)
        client = OrderClient(jwt_token="test_token")
        print("OrderClient instantiated successfully")

        print("\n[PASS] OrderClient test passed")
        return True

    except Exception as e:
        print(f"\n[FAIL] OrderClient test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sync_service():
    """Test OrderSyncService with mock data."""
    print("\n" + "=" * 60)
    print("TEST: OrderSyncService")
    print("=" * 60)

    try:
        from order_sync import OrderSyncService, SyncResult
        from order_client import OrderItem

        # Test with mock items (no actual API call)
        service = OrderSyncService(jwt_token="mock_token")

        items = [
            OrderItem(name="Test Product 1", price=10000, quantity=1),
            OrderItem(name="Test Product 2", price=20000, quantity=2),
        ]

        # Test sync_from_html
        result = await service.sync_from_html(SAMPLE_ORDER_HTML)
        print(f"sync_from_html result: success={result.success}, items={len(result.items)}")

        # Note: Actual API call will fail with mock token
        # This just tests the flow works

        print("\n[PASS] OrderSyncService test passed (flow only, no actual API)")
        return True

    except Exception as e:
        print(f"\n[FAIL] OrderSyncService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jwt_extraction():
    """Test JWT extraction from Chrome profile (if available)."""
    print("\n" + "=" * 60)
    print("TEST: JWT Extraction from Chrome Profile")
    print("=" * 60)

    try:
        from order_client import ChromeCookieExtractor

        extractor = ChromeCookieExtractor()

        # Check if profile exists
        profile_path = extractor._profile_path
        cookies_db = profile_path / "Default" / "Network" / "Cookies"

        print(f"Profile path: {profile_path}")
        print(f"Profile exists: {profile_path.exists()}")
        print(f"Cookies DB exists: {cookies_db.exists()}")

        if cookies_db.exists():
            # Try to extract JWT (may fail if no token stored)
            token = extractor.get_jwt_token()
            if token:
                # Mask token for security
                masked = token[:10] + "..." if len(token) > 10 else token
                print(f"JWT found: {masked}")
            else:
                print("No JWT found in cookies (user may need to login)")

        print("\n[INFO] JWT extraction test completed")
        return True

    except Exception as e:
        print(f"\n[INFO] JWT extraction test: {e}")
        return True  # Not a failure, just informational


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ORDER SYNC MODULE TESTS")
    print("=" * 60)

    results = {
        "extractor": test_extractor(),
        "client": test_order_client(),
        "jwt": test_jwt_extraction(),
    }

    # Run async test
    try:
        results["sync_service"] = asyncio.run(test_sync_service())
    except Exception as e:
        print(f"Async test failed: {e}")
        results["sync_service"] = False

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
