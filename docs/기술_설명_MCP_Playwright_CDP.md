# HearBe 프로젝트 핵심 기술 설명

## 1. MCP (Model Context Protocol)

### 개념
MCP는 **AI 모델이 외부 도구를 안전하고 체계적으로 사용할 수 있게 해주는 표준 프로토콜**입니다.

### 프로젝트에서의 역할
- AI(LLM)가 브라우저 제어 도구들을 마치 자신의 기능인 것처럼 호출할 수 있게 합니다
- "브라우저 열기", "검색어 입력", "스크롤 내리기", "클릭하기" 같은 기능들을 AI가 직접 실행할 수 있게 연결해줍니다
- **AI와 브라우저 제어 엔진(Playwright) 사이의 중간 다리 역할**

### 왜 필요한가?
- AI 모델은 기본적으로 텍스트만 생성할 수 있습니다
- 하지만 MCP를 통해 AI가 "실제 행동"을 할 수 있게 됩니다
- 예: "쿠팡에서 생수 검색해" → AI가 MCP를 통해 Playwright에게 실제 브라우저 조작 명령 전달

### 작동 방식
```
사용자 음성 → STT → LLM → MCP → Playwright → 브라우저 조작
```

---

## 2. Playwright

### 개념
Playwright는 **브라우저를 코드로 자동 조작할 수 있게 해주는 브라우저 자동화 엔진**입니다.

### 프로젝트에서의 역할
- 사람이 마우스와 키보드로 하는 모든 브라우저 작업을 코드로 실행합니다
- 쿠팡 접속, 검색어 입력, 상품 클릭, 장바구니 담기 등을 자동화합니다
- **현재 화면 상태를 이미지로 캡처**하여 Vision AI가 분석할 수 있게 합니다

### 주요 기능
```javascript
// 페이지 이동
await page.goto('https://www.coupang.com');

// 검색어 입력
await page.fill('input[name="q"]', '생수');

// 엔터 키 누르기
await page.press('input[name="q"]', 'Enter');

// 스크린샷 촬영 (Vision AI 분석용)
await page.screenshot({ path: 'screenshot.png', fullPage: true });

// 요소 클릭
await page.click('button.add-to-cart');
```

### 왜 Playwright인가?
- **크로스 브라우저 지원**: Chrome, Firefox, Safari 모두 지원
- **안정적인 자동화**: 페이지 로딩 대기, 요소 탐지 자동 처리
- **강력한 선택자**: CSS, XPath 등 다양한 방식으로 요소 찾기 가능
- **스크린샷/PDF 생성**: Vision AI와 연동하기 좋음

---

## 3. CDP (Chrome DevTools Protocol)

### 개념
CDP는 **Chrome 브라우저를 저수준에서 제어할 수 있는 공식 프로토콜**입니다.

### 프로젝트에서의 역할
- Playwright가 실제로 브라우저를 제어할 때 사용하는 **기반 프로토콜**
- 브라우저의 네트워크 요청, DOM 조작, JavaScript 실행 등을 세밀하게 제어합니다
- **MCP-Local-Server의 핵심 구성요소**

### 왜 필요한가?
- Playwright는 사용하기 쉬운 고수준 API를 제공하지만, 내부적으로는 CDP를 사용합니다
- CDP를 직접 사용하면 더 세밀한 제어가 가능합니다
- 예: 네트워크 트래픽 모니터링, 콘솔 로그 수집, 쿠키 조작 등

### 계층 구조
```
High Level: MCP (AI와 도구 연결)
    ↓
Mid Level: Playwright (브라우저 자동화 엔진)
    ↓
Low Level: CDP (브라우저 제어 프로토콜)
    ↓
Browser: Chrome/Chromium
```

---

## 전체 시스템에서의 연동

### 데이터 흐름
```
1. 사용자: "쿠팡에서 생수 검색해"
   ↓
2. STT: 음성 → 텍스트 변환
   ↓
3. LLM: 텍스트 분석 → 의도 파악
   ↓
4. MCP: AI가 "브라우저 조작" 도구 호출
   ↓
5. Playwright: 실제 브라우저 자동화 실행
   ↓
6. CDP: Chrome 브라우저에 저수준 명령 전달
   ↓
7. Browser: 쿠팡 접속, 생수 검색 실행
   ↓
8. Playwright: 검색 결과 스크린샷 촬영
   ↓
9. Vision AI/OCR: 이미지 분석 → 텍스트 추출
   ↓
10. TTS: 결과를 음성으로 변환
    ↓
11. 사용자: "검색 결과는..." 음성 출력
```

---

## 각 기술의 장단점

### MCP
**장점:**
- AI에게 실제 행동 능력 부여
- 안전하고 체계적인 도구 호출
- 확장 가능한 구조

**단점:**
- 상대적으로 새로운 프로토콜 (생태계 발전 중)
- 설정이 다소 복잡할 수 있음

### Playwright
**장점:**
- 사용하기 쉬운 고수준 API
- 안정적이고 빠른 자동화
- 크로스 브라우저 지원
- 활발한 커뮤니티

**단점:**
- 초기 설정 필요
- 브라우저 업데이트에 따른 호환성 이슈 가능성

### CDP
**장점:**
- Chrome 공식 프로토콜 (안정성)
- 매우 세밀한 제어 가능
- 강력한 디버깅 기능

**단점:**
- 저수준 API로 사용이 복잡
- Chrome/Chromium 기반 브라우저만 지원

---

## 실제 사용 예시: "쿠팡에서 생수 검색"

### 1단계: MCP 설정
```python
# MCP Server에 Playwright 도구 등록
@server.tool()
async def search_product(site: str, keyword: str):
    """쇼핑몰에서 상품 검색"""
    # Playwright 호출
    return await playwright_search(site, keyword)
```

### 2단계: AI가 MCP 통해 도구 호출
```
LLM 판단: "사용자가 쿠팡에서 생수를 검색하고 싶어 함"
→ MCP 도구 호출: search_product(site="coupang", keyword="생수")
```

### 3단계: Playwright 실행
```javascript
async function playwright_search(site, keyword) {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    // CDP를 통해 Chrome 제어
    await page.goto('https://www.coupang.com');
    await page.fill('input[name="q"]', keyword);
    await page.press('input[name="q"]', 'Enter');

    // 결과 페이지 스크린샷
    await page.screenshot({ path: 'result.png' });

    await browser.close();
}
```

### 4단계: 결과 반환
```
Playwright → MCP → LLM → TTS → 사용자
```

---

## 결론

**MCP, Playwright, CDP는 각각 다른 계층에서 작동하며 서로 협력합니다:**

- **CDP**: 브라우저의 엔진룸 (저수준 제어)
- **Playwright**: 운전대와 계기판 (실제 자동화)
- **MCP**: AI가 운전할 수 있게 해주는 인터페이스

이 세 가지 기술의 조합으로 **AI가 사람처럼 브라우저를 조작**할 수 있게 되며, 시각장애인 사용자가 **음성만으로 온라인 쇼핑의 전 과정을 완성**할 수 있게 됩니다.
