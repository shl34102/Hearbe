# API 명세서

[✔️ 인증/사용자 관리]
로그인	POST	/auth/login
RequestLogin
```json
{
  "userId": "user123",
  "password": "password123",
}
```

로그아웃	POST	/auth/logout
Authorization: Bearer {access_token}
사용자 정보 조회	GET	/auth/mypage
Authorization: Bearer {access_token}
ResponseMypage
```json
{
  "user": {
    "userId": "user1234",
    "username": "홍길동",
    "phoneNumber": "010-1234-5678",
    "userType": "USER | GENERAL",
    "lastLoginAt": "timestamp",
    "createdAt": "timestamp"
  },
  "profile": {
    "gender": "M | F",
    "height": 170.5,
    "weight": 60.2,
    "birthDate": "1999-01-01",
    "updatedAt": "timestamp"
  }
}

```
회원가입	POST	/auth/regist
RequestUserRegist 	
```json
{
    "login_id": "user123",
    "password": "Password123!",
    "password_check" : "Password123!",
    "username": "홍길동",
    "phone_number": "010-1234-5678",
    "user_type": "BLIND | GENERAL", 
    "simple_password": "1234" 
}
```
ResponseRegist 
```json
{ "code": 201, "message": "회원가입 성공", "data": { "user_id": 101 } }
```
비밀번호찾기	POST	/user/findPassword
아이디찾기	POST	/user/findId
비밀번호 변경	PATCH	/users/{id}/password
RequestUpdatePassword
```json

{
  "currentPassword": "oldPassword123!",
  "newPassword": "newStrongPassword456!"
}
```

로그인 ID 변경	PATCH	/users/{id}/login_id
RequestUpdateId
```json
{
  "newLoginId": "newUser123"
}
```
프로필 수정	PATCH	/users/{id}
RequestUpdateProfile
```json
{
  "height": 175.5,    // ERD에 존재하는 컬럼
  "weight": 70.2,     // ERD에 존재하는 컬럼
  "phone_number" : "010-1111-1111"
}
```



[✔️ 상품 및 플랫폼 검색 (Product & Platform)]
상품 상세 조회	GET	/products/{product_id}
RequestProduct
```json
{
  "product_id": 1025
}
```

ResponseProduct
```json
{
  "product_id": 1025,
  "platform": {
    "platform_id": 1,
    "shop_name": "Coupang",
    "base_url": "https://www.coupang.com"
  },
  "product_name": "농심 신라면 120g x 5개입",
  "product_url": "https://www.coupang.com/vp/products/123456",
  "external_product_id": "123456",
  "price_current": 4500,
  "product_image_url": "https://img.coupang.com/...",
  "last_synced_at": "2026-01-19T10:00:00Z"
}
```

플랫폼별 상품 동기화	POST	/products/sync
외부 쇼핑몰 상품 정보를 last_synced_at 기반 갱신
RequestSyncProducts 	
```json
{
  "platform_id": 1,
  "sync_items": [
    {
      "product_name": "농심 신라면 120g x 5개입",
      "product_url": "https://www.coupang.com/vp/products/123456",
      "external_product_id": "123456",
      "price_current": 4700,
      "product_image_url": "https://img.coupang.com/..."
    }
  ]
}
```

ResponseSyncProducts 
```json
{
  "status": "SUCCESS",
  "synced_count": 1,
  "timestamp": "2026-01-19T13:40:00Z"
}
```

플랫폼 목록 조회	GET	/platforms
ResponsePlatforms
```json
{
  "platforms": [
    {
      "platform_id": 1,
      "shop_name": "쿠팡",
      "base_url": "https://www.coupang.com",
      "api_endpoint_url": "https://api.coupang.com/v1/..."
    },
    {
      "platform_id": 2,
      "shop_name": "네이버 쇼핑",
      "base_url": "https://shopping.naver.com",
      "api_endpoint_url": null
    }
  ]
}
```


[✔️ wishlist]
찜 추가	POST	/wishlist
RequestWishlistCreate 	
```json
{
  "productId": 101,
  "platformId": 1
}

```
ResponseWishlistCreate 
```json
{
  "wishlistItemId": 55,
  "productId": 101,
  "likedAt": "2026-01-19T10:12:33"
}

```
찜 목록 조회	GET	/wishlist
RequestWishlist
Authorization: Bearer {access_token}

ResponseWishlist
```json
{
  "items": [
    {
      "wishlistItemId": 55,
      "productId": 101,
      "productName": "에어맥스 270",
      "productUrl": "https://...",
      "shop_name" : "coupang"
      "likedAt": "2026-01-19T10:12:33"
    }
  ]
}

```
찜 삭제	DELETE	/wishlist/{wishlistItemId}

request
Authorization: Bearer {access_token}


상품 기준 찜 여부 확인	GET	/wishlist/check
RequestWishlistCheck
```json
{
  "productId": 101,
  "platformId": 1
}
```

ResponseWishlistCheck
```json
{
  "liked": true,
  "wishlistItemId": 55
}

``


[✔️ 쇼핑 활동 (Cart,  Wishlist, Favorites)]

장바구니 담기	POST	/cart
RequestCart 	
```json

{
  "product_id": 1025,
  "platform_id": 1,
  "quantity": 2,
  "selected_options": {
    "color": "Black",
    "size": "100"
  },
  "product_metadata": {
    "brand": "농심",
    "category": "식품 > 라면"
  }
}
```

ResponseCart 
```json
{
  "cart_item_id": 101,
  "user_id": 1,
  "product_id": 505,
  "platform_id": 1,
  "quantity": 3, 
  "message": "장바구니에 상품이 담겼습니다.",
  "action_type": "UPDATED", 
  "created_at": "2026-01-19T15:00:00Z"
}
```

장바구니 목록	GET	/cart
ResponseCartList
```json
{
  "cart_items": [
    {
      "cart_item_id": 101,
      "product_id": 505,
      "platform_id": 1,
      "platform_name": "Coupang",
      "product_name": "농심 신라면 120g x 5개입",
      "price": 4500,
      "product_image_url": "https://img.coupang.com/...",
      "product_url": "https://www.coupang.com/vp/products/...",
      "quantity": 2,
      "selected_options": {        
        "color": "Black",
        "size": "100"
      },
      "created_at": "2026-01-19T10:00:00Z"
    }
  ],
  "total_count": 1
}
```

장바구니 수정	PATCH	/cart/{cart_item_id}
RequestCartUpdate 	
```json
{
  "quantity": 3
}
```

ResponseCartUpdate 
```json
{
  "cart_item_id": 101,
  "quantity": 3,
  "message": "수량이 변경되었습니다."
}
```
장바구니 삭제	DELETE	/cart/{cart_item_id}



[✔️ 즐겨찾기 & 음성 명령 (Favorites)]
장바구니 담기	POST	/cart
RequestCart 	
```json	

{
  "product_id": 1025,
  "platform_id": 1,
  "quantity": 2,
  "selected_options": {
    "color": "Black",
    "size": "100"
  },
  "product_metadata": {
    "brand": "농심",
    "category": "식품 > 라면"
  }
}
```
ResponseCart 
```json
{
  "cart_item_id": 101,
  "user_id": 1,
  "product_id": 505,
  "platform_id": 1,
  "quantity": 3, 
  "message": "장바구니에 상품이 담겼습니다.",
  "action_type": "UPDATED", 
  "created_at": "2026-01-19T15:00:00Z"
}
```
장바구니 목록	GET	/cart
ResponseCartList
```json
{
  "cart_items": [
    {
      "cart_item_id": 101,
      "product_id": 505,
      "platform_id": 1,
      "platform_name": "Coupang",
      "product_name": "농심 신라면 120g x 5개입",
      "price": 4500,
      "product_image_url": "https://img.coupang.com/...",
      "product_url": "https://www.coupang.com/vp/products/...",
      "quantity": 2,
      "selected_options": {        
        "color": "Black",
        "size": "100"
      },
      "created_at": "2026-01-19T10:00:00Z"
    }
  ],
  "total_count": 1
}
```

장바구니 수정	PATCH	/cart/{cart_item_id}
RequestCartUpdate 	
```json
{
  "quantity": 3
}
```

ResponseCartUpdate 
```json
{
  "cart_item_id": 101,
  "quantity": 3,
  "message": "수량이 변경되었습니다."
}
```

장바구니 삭제	DELETE	/cart/{cart_item_id}





[✔️ 주문 및 결제 (Orders)]
주문 생성	POST	/orders
RequestOrders 
```json	
{
  "cart_item_ids": [10, 11, 12],
  "total_amount": 45000,
  "payment_method": "SIMPLE_PAY",
  "shipping_address": "서울특별시 강남구 ...",
  "order_detail_url": "https://m.coupang.com/orders/history/..."
}

```
ResponseOrders 
```json
{
  "order_id": 5001,
  "pay_status": "PAID",
  "ordered_at": "2026-01-19T14:30:00Z",
  "items": [
    {
      "product_name": "농심 신라면 5입",
      "price_at_order": 4500,
      "quantity": 2
    }
  ]
}
```
내 주문 내역	GET	/orders/me
ResponseMe
```json
{
  "orders": [
    {
      "order_id": 5001,
      "total_amount": 45000,
      "pay_status": "PAID",
      "order_date": "2026-01-19",
      "representative_item_name": "농심 신라면 외 2건"
    }
  ]
}
```


[✔️ 보호자 공유 세션 (Sharing Session)]
공유 세션 시작	POST	/sharing/sessions
RequestSessions 	
```json	
{
  "host_user_id": 1,
  "session_type": "SHOPPING_ASSIST"
}
```
ResponseSessions 
```json
{
  "sharing_session_id": 201,
  "meeting_code": "XY72B9",
  "session_status": "active",
  "expires_at": "2026-01-19T15:30:00Z"
}
```
세션 참가	POST	/sharing/sessions/join
RequestSessionsJoin 
```json	
{
  "meeting_code": "XY72B9",
  "user_id": 1,
}
```
ResponseSessionsJoin 
```json
{
  "sharing_session_id": 201,
  "is_media_sharing" : true,
  "is_audio_sharing" : true,
  "host_sdp_offer" : true,
  "status": "connected",
  "host_username": "홍길동",
  "webrtc_config": {
    "ice_servers": [서버 주소 리스트]
  }
}
```
세션 종료	PATCH	/sharing/sessions/{id}/end
ResponseSessionsEnd 
```json
{
  "sharing_session_id": 201,
  "duration_seconds": 1200,
  "session_status": "completed",
  "ended_at": "2026-01-19T14:50:00Z",
  "session_closed": "host or guest"
}
```

