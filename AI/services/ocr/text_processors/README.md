# OCR Text Processors

상품 이미지에서 OCR 텍스트를 추출하고, LLM을 사용해 요약을 생성하는 파이프라인입니다.

---

## 📊 구현 현황

| 기능 | 상태 | 담당 모듈 |
|------|------|----------|
| 한국어 OCR 처리 | ✅ 완료 | `korean_ocr.py` |
| 긴 이미지 분할 처리 | ✅ 완료 | `long_image_processor.py` |
| 텍스트 전처리/필터링 | ✅ 완료 | `ocr_text_preprocessor.py` |
| 텍스트 병합 | ✅ 완료 | `ocr_text_merger.py` |
| 상품 타입 감지 | ✅ 완료 | `product_type_detector.py` |
| LLM 요약 생성 | ✅ 완료 | `ocr_llm_summarizer.py` |
| 이미지 URL 필터링/다운로드 | ✅ 완료 | `image_fetcher.py` |
| 통합 파이프라인 | ✅ 완료 | `ocr_pipeline.py` |
| **WebSocket 연동** | ✅ 완료 | `services/summarizer/` |
| **HTML 파서** | ✅ 완료 | `services/summarizer/html_parser.py` |
| **MCP → OCR → TTS 통합** | ✅ 완료 | `api/websocket.py` |

> 📖 상세 문서: [MCP_OCR_INTEGRATION.md](/docs/MCP_OCR_INTEGRATION.md)

---

## 🚀 빠른 시작

```bash
# 단일 이미지 처리
python ocr_pipeline.py --input 샴푸.jpg

# 여러 이미지 병합 처리
python ocr_pipeline.py --inputs img1.jpg img2.jpg img3.jpg

# URL 기반 처리
python ocr_pipeline.py --urls "https://..." --site coupang
```

### Python에서 사용

```python
from ocr_pipeline import process_product_image, process_product_from_urls

# 단일 이미지
result = process_product_image("샴푸.jpg")
print(result["summary"])

# URL 기반 (MCP Playwright에서 추출한 URL 리스트)
result = process_product_from_urls(urls, site="coupang")
print(result["summary"])  # TTS용 요약
```

---

## 📁 파일 구조

| 파일 | 역할 |
|-----|-----|
| `ocr_pipeline.py` | **통합 파이프라인 (메인 진입점)** |
| `korean_ocr.py` | PaddleOCR 기반 OCR + 긴 이미지 자동 분할 |
| `long_image_processor.py` | 슬라이딩 윈도우 분할 OCR |
| `ocr_text_preprocessor.py` | 텍스트 정제/필터링 |
| `ocr_text_merger.py` | 여러 OCR 결과 병합 + 중복 제거 |
| `product_type_detector.py` | 제품 타입 분류 (30개 카테고리) |
| `ocr_llm_summarizer.py` | 타입별 프롬프트 + LLM 요약 |
| `image_fetcher.py` | 이미지 URL 필터링/다운로드 |
| `extract_rec_texts.py` | OCR JSON에서 텍스트 추출 유틸 |

---

## 📊 파이프라인 흐름

```
[이미지 입력]
      ↓
[korean_ocr] OCR 처리 (긴 이미지는 자동 분할)
      ↓
[ocr_text_merger] 텍스트 병합 + 중복 제거
      ↓
[ocr_text_preprocessor] 전처리 (노이즈/저신뢰도 제거)
      ↓
[product_type_detector] 상품 타입 감지
      ↓
[ocr_llm_summarizer] LLM 요약 생성
      ↓
[TTS용 요약 텍스트 출력]
```

---

## 🚧 미구현 부분 (TODO)

> **팀원 분들께**: 아래 기능들은 프론트엔드/Playwright 연동이 필요합니다.

### 1. 웹 연동 - 자동 OCR 트리거

**현재 상태:**
- 이미지 URL 리스트를 수동으로 전달해야 함
- `process_product_from_urls(urls)` 형태로 직접 호출 필요

**필요한 구현:**
- 상품 페이지 접속 시 자동으로 OCR 파이프라인 실행
- URL 패턴 감지 (쿠팡/네이버 상품 페이지인지 판별)
- 트리거 조건 정의 (페이지 로드 완료, 버튼 클릭 등)

---

### 2. MCP Playwright 통합

**현재 상태:**
- CSS 셀렉터만 정의됨 (`image_fetcher.py`)
  - 쿠팡: `.product-detail-content-inside img`
  - 네이버: `#INTRODUCE img`

**필요한 구현:**
```python
# 예상 구현 흐름
async def extract_product_images(page_url: str):
    # 1. Playwright로 페이지 접속
    # 2. CSS 셀렉터로 img 태그 추출
    # 3. src 속성에서 URL 추출
    # 4. process_product_from_urls() 호출
    pass
```

**구현 시 참고:**
- `image_fetcher.get_selector(site)` - 사이트별 CSS 셀렉터 반환
- `image_fetcher.filter_product_images(urls)` - 광고/배너 URL 필터링

---

### 3. API 인터페이스

**현재 상태:**
- CLI 및 Python 함수 호출만 지원

**필요한 구현 (선택):**
- REST API 엔드포인트 (Flask/FastAPI)
- WebSocket 인터페이스 (실시간 처리)

**예상 API 형태:**
```
POST /api/ocr/process
Body: { "urls": ["...", "..."], "site": "coupang" }
Response: { "summary": [...], "product_name": "..." }
```

---

## 📝 연동 시 필요한 입출력 형식

### 입력 (OCR 파이프라인 호출 시)

```python
# 방법 1: 이미지 경로
process_product_image("path/to/image.jpg")

# 방법 2: URL 리스트 (Playwright에서 추출)
process_product_from_urls(
    image_urls=["https://...", "https://..."],
    site="coupang"  # 또는 "naver", "auto"
)
```

### 출력 (TTS에서 사용)

```json
{
  "product_type": "BEAUTY_HAIRCARE",
  "product_name": "케라시스 샴푸",
  "summary": [
    "이 제품은 케라시스 데미지 클리닉 샴푸입니다.",
    "손상된 모발을 위한 집중 케어 샴푸입니다.",
    "용량은 600ml입니다."
  ],
  "keywords": {
    "용량": {"answer": "600ml", "status": "found"},
    "성분": {"answer": "케라틴, 아르간오일", "status": "found"}
  }
}
```

---

## 환경 변수 (.env)

```env
GMS_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5-mini
```

---

## 설치 의존성

```bash
# PaddlePaddle (GPU)
python -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# PaddleOCR + 기타
python -m pip install paddleocr pillow requests python-dotenv
```
