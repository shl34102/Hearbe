# Order + Product Sync (AI -> Backend)

This document summarizes the two backend calls the AI server makes after a successful Coupang order flow:

1. `POST /api/orders` (order + items)
2. `POST /api/product` (last extracted product_detail metadata)

Both calls use the same access token:

`Authorization: Bearer <accessToken>`

Base URL:

`https://i14d108.p.ssafy.io/api`

## 1) Create Order

`POST /api/orders`

Request body:

```json
{
  "platform_id": 1,
  "order_url": "https://mc.coupang.com/ssr/desktop/order/21100169998857",
  "items": [
    {
      "name": "롯데칠성음료 하늘샘 생수 무라벨, 2L, 18개",
      "price": 6750,
      "quantity": 1,
      "url": "https://www.coupang.com/vp/products/7900128179?itemId=...",
      "img_url": "https://thumbnail.coupangcdn.com/thumbnails/remote/320x320ex/image/...",
      "deliver_url": "https://www.coupang.com/tracking/...",
      "coupang_product_number": "7689270513 - 20972233691",
      "category_path": [
        "식품",
        "사과식초/땅콩버터 외",
        "생수/음료",
        "생수",
        "국산생수"
      ]
    }
  ]
}
```

Notes:
- `platform_id=1` is Coupang.
- `order_url` is the current order detail page URL.

## 2) Sync Product Metadata

`POST /api/product`

Request body (from `session.context["product_detail"]`):

```json
{
  "name": "탐사 샘물, 500ml, 40개",
  "category_path": [
    "식품",
    "사과식초/땅콩버터 외",
    "생수/음료",
    "생수",
    "국산생수"
  ],
  "coupang_product_number": "7689270513 - 20972233691"
}
```

Notes:
- `coupang_product_number` is derived from `product_detail["coupang_product_info_kv"]["쿠팡상품번호"]` (fallback parses `coupang_product_info`).
- The AI server sends this best-effort only after `POST /api/orders` succeeds.
