# -*- coding: utf-8 -*-
"""
E2E Flow Test: Checkout -> Order Sync -> DB Saved

Tests the complete flow:
1. Simulate checkout completion with order items
2. Sync order to backend via API
3. Verify order saved by fetching order history

Usage:
    cd AI/api/order
    python test_e2e_flow.py

Requirements:
    - Backend server running at https://i14d108.p.ssafy.io
    - Valid JWT token (from hearbe service)
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
_current_dir = Path(__file__).resolve().parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Test JWT token from hearbe service (user_id: 3, username: 1234...)
TEST_JWT_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxYTJiIiwiYXV0aCI6IlJPTEVfVVNFUiIsInVzZXJJZCI6MywidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc3MDE4MjQzNSwiZXhwIjoxNzcwMTg2MDM1fQ.Ma57qYgn1FJWbrnP4vjdS59eZnpd_fmxVQAwdDVB8PE"

# Backend API URL configuration
# For LOCAL testing: run backend on your machine, use localhost
# For REMOTE testing: use deployed server (requires nginx fix)
LOCAL_BACKEND_URL = "http://localhost:8080"
REMOTE_BACKEND_URL = "https://i14d108.p.ssafy.io/api"

# Change this to switch between local/remote testing
USE_LOCAL = False  # Set to False to test against deployed server

BACKEND_URL = LOCAL_BACKEND_URL if USE_LOCAL else REMOTE_BACKEND_URL


def create_test_order_items():
    """Create mock order items simulating checkout completion."""
    from order_client import OrderItem

    timestamp = datetime.now().strftime("%H%M%S")

    return [
        OrderItem(
            name=f"[E2E Test] Coupang Product A - {timestamp}",
            price=29900,
            quantity=1,
            url="https://www.coupang.com/vp/products/12345",
            img_url="https://thumbnail.coupang.com/example1.jpg",
            deliver_url="https://delivery.coupang.com/track/123",
        ),
        OrderItem(
            name=f"[E2E Test] Coupang Product B - {timestamp}",
            price=15000,
            quantity=2,
            url="https://www.coupang.com/vp/products/67890",
            img_url="https://thumbnail.coupang.com/example2.jpg",
            deliver_url=None,
        ),
    ]


async def test_order_creation():
    """Test: Create order via API."""
    print("\n" + "=" * 60)
    print("STEP 1: Create Order (Simulate Checkout Completion)")
    print("=" * 60)

    from order_client import OrderClient
    from order_sync import OrderSyncService

    # Create client with test JWT
    client = OrderClient(
        backend_url=BACKEND_URL,
        jwt_token=TEST_JWT_TOKEN,
    )

    # Create test items
    items = create_test_order_items()
    print(f"Created {len(items)} test order items:")
    for i, item in enumerate(items):
        print(f"  {i+1}. {item.name} - {item.price}won x {item.quantity}")

    # Send to backend
    print("\nSending order to backend...")
    result = await client.create_order(items=items, platform_id=1)

    if result.get("success"):
        print("[SUCCESS] Order created!")
        print(f"Response: {result.get('data')}")
        return True, result.get("data")
    else:
        print(f"[FAILED] {result.get('error')}")
        print(f"Status code: {result.get('status_code')}")
        return False, result


async def test_order_retrieval():
    """Test: Retrieve orders to verify saved."""
    print("\n" + "=" * 60)
    print("STEP 2: Verify Order Saved (Get My Orders)")
    print("=" * 60)

    from order_client import OrderClient

    client = OrderClient(
        backend_url=BACKEND_URL,
        jwt_token=TEST_JWT_TOKEN,
    )

    print("Fetching order history...")
    result = await client.get_my_orders()

    if result.get("success"):
        data = result.get("data", {})
        orders = data.get("data", {}).get("orders", [])
        print(f"[SUCCESS] Found {len(orders)} orders")

        if orders:
            print("\nMost recent order:")
            recent = orders[0]
            print(f"  Order ID: {recent.get('order_id')}")
            print(f"  Date: {recent.get('ordered_at')}")
            print(f"  Platform: {recent.get('platform_id')}")
            print(f"  Items: {len(recent.get('items', []))}")

            for item in recent.get("items", []):
                print(f"    - {item.get('name')}: {item.get('price')}won x {item.get('quantity')}")

        return True, orders
    else:
        print(f"[FAILED] {result.get('error')}")
        return False, result


async def test_sync_service_flow():
    """Test: Full sync service flow."""
    print("\n" + "=" * 60)
    print("STEP 3: Test OrderSyncService (Full Flow)")
    print("=" * 60)

    from order_sync import OrderSyncService
    from order_client import OrderItem

    service = OrderSyncService(
        backend_url=BACKEND_URL,
        jwt_token=TEST_JWT_TOKEN,
    )

    # Simulate checkout completion with order items
    items = [
        OrderItem(
            name=f"[SyncService Test] Product - {datetime.now().strftime('%H%M%S')}",
            price=9900,
            quantity=1,
        )
    ]

    print(f"Syncing {len(items)} items via OrderSyncService...")
    result = await service.sync_items(items)

    if result.success:
        print(f"[SUCCESS] Synced {result.synced_count} items")
        print(f"Backend response: {result.backend_response}")
        return True
    else:
        print(f"[FAILED] {result.error}")
        return False


async def test_html_extraction_and_sync():
    """Test: Extract from HTML and sync."""
    print("\n" + "=" * 60)
    print("STEP 4: Test HTML Extraction -> Sync")
    print("=" * 60)

    from order_sync import OrderSyncService

    # Sample Coupang order HTML
    sample_html = """
    <div class="order-list-item">
        <span class="order-date">2025.02.04</span>
        <div class="product-item">
            <a class="product-name" href="/vp/products/999">
                [HTML Extract Test] Coupang Item
            </a>
            <span class="price">19,900원</span>
            <span class="quantity">수량: 1</span>
        </div>
    </div>
    """

    service = OrderSyncService(
        backend_url=BACKEND_URL,
        jwt_token=TEST_JWT_TOKEN,
    )

    print("Extracting orders from HTML...")
    result = await service.sync_from_html(sample_html)

    if result.success:
        print(f"[SUCCESS] Extracted and synced {result.synced_count} items")
        for item in result.items:
            print(f"  - {item.name}: {item.price}won")
        return True
    else:
        print(f"[FAILED] {result.error}")
        return False


async def test_backend_connectivity():
    """Test backend connectivity."""
    print("\n" + "=" * 60)
    print("STEP 0: Backend Connectivity Test")
    print("=" * 60)
    print(f"Mode: {'LOCAL' if USE_LOCAL else 'REMOTE'}")
    print(f"URL: {BACKEND_URL}")

    import httpx

    # Simple health check first
    print("\nTesting connection...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try health endpoint
            health_url = f"{BACKEND_URL}/health"
            try:
                response = await client.get(health_url)
                print(f"  GET {health_url}: {response.status_code}")
            except Exception:
                print(f"  GET {health_url}: Connection failed")

            # Try orders endpoint with auth
            orders_url = f"{BACKEND_URL}/orders"
            headers = {
                "Authorization": f"Bearer {TEST_JWT_TOKEN}",
                "Content-Type": "application/json",
            }
            test_body = {
                "platform_id": 1,
                "items": [{"name": "connectivity test", "price": 100, "quantity": 1}]
            }
            response = await client.post(orders_url, json=test_body, headers=headers)
            print(f"  POST {orders_url}: {response.status_code}")

            if response.status_code in (200, 201):
                print("  [OK] Backend is reachable and accepts orders")
                return BACKEND_URL
            elif response.status_code == 401:
                print("  [AUTH] JWT token expired - get a fresh token")
            elif response.status_code == 403:
                print("  [FORBIDDEN] Check JWT permissions")
            else:
                print(f"  Response: {response.text[:200]}")

    except httpx.ConnectError:
        print("  [ERROR] Cannot connect to backend")
        if USE_LOCAL:
            print("  Make sure backend is running: cd Backend && ./gradlew bootRun")
    except Exception as e:
        print(f"  [ERROR] {e}")

    return None


async def run_e2e_tests():
    """Run all E2E tests."""
    print("\n" + "=" * 70)
    print("E2E FLOW TEST: Checkout -> Order Sync -> DB Saved")
    print("=" * 70)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"JWT Token: {TEST_JWT_TOKEN[:20]}...")
    print("=" * 70)

    # Test backend connectivity first
    working_url = await test_backend_connectivity()
    if not working_url:
        print("\n[SKIP] Backend not reachable, skipping API tests")
        print("To test locally: set USE_LOCAL=True and run backend")
        return 1

    results = {}

    # Test 1: Create order
    try:
        success, data = await test_order_creation()
        results["order_creation"] = success
    except Exception as e:
        print(f"[ERROR] {e}")
        results["order_creation"] = False

    # Test 2: Retrieve orders
    try:
        success, data = await test_order_retrieval()
        results["order_retrieval"] = success
    except Exception as e:
        print(f"[ERROR] {e}")
        results["order_retrieval"] = False

    # Test 3: Sync service flow
    try:
        results["sync_service"] = await test_sync_service_flow()
    except Exception as e:
        print(f"[ERROR] {e}")
        results["sync_service"] = False

    # Test 4: HTML extraction and sync
    try:
        results["html_extract_sync"] = await test_html_extraction_and_sync()
    except Exception as e:
        print(f"[ERROR] {e}")
        results["html_extract_sync"] = False

    # Summary
    print("\n" + "=" * 70)
    print("E2E TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("All E2E tests passed! Flow verified:")
        print("  Checkout Complete -> Extract Items -> POST /orders -> DB Saved")
    else:
        print("Some tests failed. Check backend connection and JWT token.")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_e2e_tests()))
