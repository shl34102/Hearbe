# MCP → OCR → TTS 통합 파이프라인

> **업데이트**: 2025-01-26
> **상태**: ✅ 구현 완료

---

## 📋 개요

MCP 결과를 받아 HTML 파싱과 OCR 처리를 통해 TTS 응답을 생성하는 통합 파이프라인입니다.

### 처리 흐름

```
MCP 결과 수신
    │
    ├─── Path 1: HTML 파싱 → TTS #1 (즉시 응답, ~1-2초)
    │    - 상품명, 가격, 배송정보, 리뷰수
    │    - OCR 없이 바로 텍스트 추출
    │
    └─── Path 2: OCR 처리 → TTS #2 (백그라운드, ~7초)
         - 상세 이미지 전체 OCR
         - 영양정보, 성분, 사용법 등 추출
         - 결과를 세션에 저장 (Q&A용)
```

---

## 📁 파일 구조

```
services/summarizer/
├── __init__.py           # 모듈 export
├── html_parser.py        # HTML 파싱 (쿠팡/네이버)
└── ocr_integrator.py     # OCR 파이프라인 통합

api/
└── websocket.py          # _handle_mcp_result() 수정됨
```

---

## 🔧 구현 상세

### 1. HTML 파서 (`html_parser.py`)

쿠팡/네이버 상품 페이지 HTML을 파싱합니다.

```python
from services.summarizer import parse_product_html, format_for_tts

# HTML 파싱
product_info = parse_product_html(html_content, site="coupang")

# TTS용 텍스트 변환
tts_text = format_for_tts(product_info, include_details=True)
# "상품명: 모던프로 3M 겨울 비니. 가격: 11,950원. 배송: 내일(화) 도착 보장. 리뷰 733개."
```

**추출 정보:**
| 필드 | 쿠팡 셀렉터 | 네이버 셀렉터 |
|------|------------|--------------|
| 상품명 | `.product-title__name` | `._3oDjSvLfl0` |
| 가격 | `.final-price` | `._1LY7DqCnwR` |
| 배송정보 | `.delivery-date` | `._3H-4dFHHhW` |
| 리뷰수 | `.rating-count` | `._2N_MalQHrs` |
| 상세이미지 | `.product-detail-content-inside img` | `#INTRODUCE img` |

### 2. OCR 통합 (`ocr_integrator.py`)

기존 OCR 파이프라인을 비동기로 래핑합니다.

```python
from services.summarizer import get_ocr_integrator

ocr = get_ocr_integrator()

# 모든 이미지 한번에 처리
result = await ocr.process_single_batch(image_urls, site="coupang")

print(result.summary)    # ["이 제품은...", "성분은...", ...]
print(result.keywords)   # {"성분": {...}, "영양정보": {...}}
```

### 3. WebSocket 핸들러 수정

`_handle_mcp_result()` 메서드가 수정되었습니다:

```python
async def _handle_mcp_result(self, session_id: str, data: Dict[str, Any]):
    # MCP 결과에서 HTML과 이미지 URL 추출
    html_content = page_data.get("html")
    detail_images = page_data.get("detail_images") or []

    # Path 1: HTML 파싱 → 즉시 TTS
    if html_content:
        product_info = parse_product_html(html_content, site=site)
        await self._send_tts_response(session_id, format_for_tts(product_info))

    # Path 2: OCR 처리 → 백그라운드 TTS
    if detail_images:
        asyncio.create_task(
            self._process_ocr_batch(session_id, detail_images, page_url)
        )
```

---

## 📡 MCP 결과 형식

MCP 서버에서 다음 형식으로 데이터를 전달해야 합니다:

```json
{
  "type": "mcp_result",
  "data": {
    "success": true,
    "page_data": {
      "url": "https://www.coupang.com/vp/products/123456",
      "html": "<html>...</html>",
      "detail_images": [
        "https://thumbnail.coupang.com/.../1.jpg",
        "https://thumbnail.coupang.com/.../2.jpg"
      ]
    }
  }
}
```

**필수 필드:**
- `page_data.html`: 상품 페이지 HTML (또는 필요한 부분만)
- `page_data.detail_images`: 상세 이미지 URL 리스트

---

## 📤 WebSocket 응답

### TTS 응답 (HTML 파싱 결과)
```json
{
  "type": "tts_chunk",
  "data": {
    "audio": "...",
    "is_final": true
  }
}
```

### OCR 진행 상황
```json
{
  "type": "ocr_progress",
  "data": {
    "status": "started|ocr_completed|completed|error",
    "progress": 0-100,
    "total_images": 5,
    "error": null
  }
}
```

---

## 🧪 테스트 방법

### 1. 서버 실행

```bash
cd /home/murphy/S14P11D108/AI
docker-compose up --build
```

### 2. WebSocket 테스트 (wscat)

```bash
# wscat 설치
npm install -g wscat

# 연결
wscat -c ws://localhost:8000/ws/test-session

# MCP 결과 전송 (테스트)
{"type": "mcp_result", "data": {"success": true, "page_data": {"html": "<span class=\"product-title__name\">테스트 상품</span><span class=\"final-price\">10,000원</span>", "detail_images": []}}}
```

### 3. Python 테스트

```python
import asyncio
from services.summarizer import parse_product_html, format_for_tts

# HTML 파서 테스트
html = '''
<span class="product-title__name">모던프로 3M 겨울 비니</span>
<span class="final-price">11,950원</span>
<span class="delivery-date">내일(화) 1/27 도착 보장</span>
<span class="rating-count">733</span>
'''

info = parse_product_html(html, site="coupang")
print(f"상품명: {info.product_name}")
print(f"가격: {info.price}")
print(f"TTS: {format_for_tts(info)}")
```

---

## 🔄 Q&A 연동 (추후 구현)

OCR 결과는 세션에 저장되어 사용자 질의응답에 활용됩니다:

```python
# 세션에 저장된 OCR 결과
ocr_result = session.context.get("ocr_result")

# 사용자 질문: "성분이 뭐야?"
# → ocr_result["keywords"]["성분"]["answer"] 반환
```

---

## 📝 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2025-01-26 | 초기 구현 - HTML 파서, OCR 통합, WebSocket 연동 |
