# Order Sync Module - Coupang 주문 동기화

> **업데이트**: 2026-02-04
> **상태**: E2E 테스트 완료

---

## 개요

Coupang 결제 완료 후 주문 정보를 자동으로 Backend DB에 동기화하는 모듈입니다.

### 처리 흐름

```
Checkout 완료
    │
    ├─── 1. Chrome Cookies에서 JWT 추출
    │    - access_token, jwt 등 검색
    │    - DPAPI/AES-GCM 복호화 (Windows)
    │
    ├─── 2. 주문 정보 추출 (order_extractor)
    │    - HTML 파싱 또는 MCP 결과 사용
    │    - 상품명, 가격, 수량, 이미지 URL 등
    │
    └─── 3. Backend API 호출 (order_client)
         - POST /api/orders
         - JWT Bearer 인증
         - 주문 데이터 저장
```

---

## 파일 구조

```
AI/api/order/
├── __init__.py           # Module exports
├── order_client.py       # HTTP client for /orders API
├── order_extractor.py    # Coupang order HTML parser
├── order_sync.py         # Orchestrator (extraction + sync)
├── test_order_sync.py    # Unit tests
└── test_e2e_flow.py      # E2E integration test
```

---

## 구현 상세

### 1. OrderClient (`order_client.py`)

Backend `/orders` API와 통신하는 HTTP 클라이언트입니다.

```python
from api.order import OrderClient, OrderItem

# JWT 자동 추출 (Chrome cookies)
client = OrderClient()

# 또는 수동 JWT 제공
client = OrderClient(jwt_token="eyJhbG...")

# 주문 생성
items = [
    OrderItem(
        name="상품명",
        price=15000,
        quantity=2,
        url="https://coupang.com/...",
        img_url="https://thumbnail...",
    )
]
result = await client.create_order(items=items, platform_id=1)

# 내 주문 조회
orders = await client.get_my_orders()
```

**주요 클래스:**

| Class | Description |
|-------|-------------|
| `OrderItem` | 단일 주문 아이템 DTO |
| `OrderCreateRequest` | POST /orders 요청 body |
| `ChromeCookieExtractor` | Chrome 쿠키에서 JWT 추출 |
| `OrderClient` | HTTP 클라이언트 (async) |

### 2. OrderExtractor (`order_extractor.py`)

Coupang 주문 완료 페이지에서 주문 정보를 추출합니다.

```python
from api.order import OrderExtractor, ExtractionResult

extractor = OrderExtractor()

# HTML에서 추출
result: ExtractionResult = extractor.extract_from_html(html_content)

if result.success:
    for item in result.items:
        print(f"{item.name}: {item.price}won x {item.quantity}")
else:
    print(f"Error: {result.error}")
```

**추출 정보:**

| Field | CSS Selector | Description |
|-------|--------------|-------------|
| name | `.prod-name`, `._3Xkxp` | 상품명 |
| price | `.prod-price`, `._1y4bU` | 가격 |
| quantity | `.prod-qty`, `._1mHVL` | 수량 |
| img_url | `.prod-img img`, `._1P_vM img` | 상품 이미지 |

### 3. OrderSync (`order_sync.py`)

추출과 API 호출을 통합하는 오케스트레이터입니다.

```python
from api.order import OrderSync, SyncResult

sync = OrderSync()

# HTML에서 추출 후 동기화
result: SyncResult = await sync.sync_from_html(html_content)

# MCP 결과에서 직접 동기화
result = await sync.sync_from_mcp_result(mcp_data)

if result.success:
    print(f"Order #{result.order_id} synced!")
    print(f"Items: {len(result.items)}")
```

---

## API 스펙

### POST /api/orders

주문 생성 요청

**Request:**
```json
{
  "platform_id": 1,
  "items": [
    {
      "name": "상품명",
      "price": 15000,
      "quantity": 2,
      "url": "https://...",
      "img_url": "https://...",
      "deliver_url": null,
      "coupang_product_number": "7689270513 - 20972233691",
      "category_path": [
        "Food",
        "Beverages",
        "Water"
      ]
    }
  ]
}
```

**Response (201):**
```json
{
  "order_id": 123,
  "pay_status": "PAID",
  "ordered_at": "2026-02-04T10:30:00",
  "items": [
    {
      "order_item_id": 456,
      "name": "상품명",
      "price": 15000,
      "quantity": 2,
      "url": "https://...",
      "img_url": "https://..."
    }
  ]
}
```

**Error Responses:**
- `401`: JWT 토큰 만료/무효
- `400`: 잘못된 요청 데이터

### GET /api/orders/me

사용자 주문 내역 조회

**Response (200):**
```json
{
  "orders": [
    {
      "order_id": 123,
      "ordered_at": "2026-02-04",
      "order_url": "https://...",
      "platform_id": 1,
      "items": [...]
    }
  ]
}
```

---

## JWT 인증

### Chrome Cookie 추출

Windows에서 Chrome 쿠키를 자동으로 추출합니다.

```python
extractor = ChromeCookieExtractor(
    profile_path=Path("MCP/.mcp_chrome_profile")
)
token = extractor.get_jwt_token(domain="i14d108.p.ssafy.io")
```

**검색 쿠키 이름:** `access_token`, `accessToken`, `jwt`, `token`, `Authorization`

**복호화 방식:**
- Chrome 80+: AES-GCM (`v10`/`v11` prefix)
- 이전 버전: Windows DPAPI

### 수동 토큰 제공

테스트나 서버 환경에서는 직접 토큰을 제공합니다:

```python
client = OrderClient(jwt_token="eyJhbG...")
```

---

## 테스트

### Unit Test

```bash
cd AI/api/order
python -m pytest test_order_sync.py -v
```

### E2E Test

```bash
cd AI/api/order
python test_e2e_flow.py
```

**테스트 항목:**
1. Backend 연결 확인
2. 주문 생성 (POST /orders)
3. 주문 조회 (GET /orders/me)
4. HTML 파싱

**설정:**
```python
# test_e2e_flow.py
USE_LOCAL = False  # True: localhost:8080, False: i14d108.p.ssafy.io
TEST_JWT_TOKEN = "eyJhbG..."  # 유효한 JWT 토큰 필요
```

---

## Checkout Flow 연동

MCP checkout 완료 시 자동 동기화 (구현 예정):

```python
# MCP server checkout handler
async def on_checkout_complete(session_id: str, page_data: dict):
    sync = OrderSync()

    result = await sync.sync_from_mcp_result({
        "html": page_data.get("html"),
        "url": page_data.get("url"),
    })

    if result.success:
        logger.info(f"Order synced: #{result.order_id}")
    else:
        logger.error(f"Sync failed: {result.error}")
```

---

## 설정

### 환경 변수

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `https://i14d108.p.ssafy.io/api` | Backend API URL |
| `CHROME_PROFILE_PATH` | `MCP/.mcp_chrome_profile` | Chrome profile 경로 |

### Platform ID

| ID | Platform |
|----|----------|
| 1 | Coupang |

---

## 의존성

```
httpx>=0.24.0
beautifulsoup4>=4.12.0
pywin32  # Windows only (cookie decryption)
cryptography  # Chrome 80+ cookie decryption
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-02-04 | 초기 구현 - OrderClient, OrderExtractor, OrderSync, E2E 테스트 완료 |
