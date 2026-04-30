# 플로우 엔진 가이드

> 사이트별 회원가입/결제 플로우 정의 및 실행 가이드

## 개요

**플로우 엔진**은 복잡한 쇼핑 프로세스(회원가입, 결제)를 **단계별 상태 머신**으로 관리합니다.

### 주요 기능
- 사이트별 플로우 정의 (JSON)
- 단계별 TTS 안내
- MCP 도구 자동 호출
- 사용자 입력 검증
- 에러 처리 및 재시도

---

## 플로우 타입

### 0. `visit` - 사이트 접속 시 로그인
각 쇼핑 사이트에 접속하면 회원인지 묻고 회원이면 로그인 진행
로그인 정보 저장이 가능하다면 저장을 권장하고 저장 여부 묻기
저장 시 로그인 정보 저장 버튼 클릭

### 1. `search` - 상품 검색
간단한 검색 명령, 플로우 불필요 (LLM 직접 처리)

### 2. `checkout` - 결제
단계별 안내 필요 (배송지, 결제 수단, 확인)

### 3. `signup` - 회원가입
복잡한 입력 필드 (이메일, 비밀번호, 본인인증)

---

## 플로우 JSON 구조

### 기본 템플릿

```json
{
  "flow_id": "coupang_checkout",
  "flow_type": "checkout",
  "site": "coupang",
  "version": "1.0",
  "steps": [
    {
      "step_id": "start",
      "step_name": "장바구니 확인",
      "prompt": "장바구니에 담긴 상품을 확인하시겠습니까?",
      "actions": [
        {
          "type": "tts",
          "text": "장바구니에 {item_count}개의 상품이 있습니다. 결제를 진행하시겠습니까?"
        },
        {
          "type": "tool_call",
          "tool_name": "navigate_to_url",
          "arguments": {
            "url": "https://cart.coupang.com/cartView.pang?traceId=mkeouvhh"
          }
        }
      ],
      "required_fields": [],
      "validation": {
        "type": "user_confirmation",
        "options": ["네", "아니오"]
      },
      "next_step": {
        "default": "address_input",
        "on_negative": "cancel"
      }
    },
    {
      "step_id": "address_input",
      "step_name": "배송지 입력",
      "prompt": "배송지 주소를 말씀해주세요.",
      "actions": [
        {
          "type": "tts",
          "text": "배송지 주소를 말씀해주세요. 예: 서울시 강남구 테헤란로 123"
        }
      ],
      "required_fields": ["address", "phone"],
      "validation": {
        "type": "address",
        "fields": {
          "address": {
            "min_length": 10,
            "pattern": "^[가-힣0-9\\s-]+$"
          },
          "phone": {
            "pattern": "^010-\\d{4}-\\d{4}$"
          }
        }
      },
      "next_step": {
        "default": "payment_method"
      }
    },
    {
      "step_id": "payment_method",
      "step_name": "결제 수단 선택",
      "prompt": "결제 수단을 선택하세요. 신용카드, 계좌이체, 간편결제 중 선택하세요.",
      "actions": [
        {
          "type": "tts",
          "text": "결제 수단을 선택하세요."
        },
        {
          "type": "tool_call",
          "tool_name": "get_text",
          "arguments": {
            "selector": ".payment-methods"
          }
        }
      ],
      "required_fields": ["payment_method"],
      "validation": {
        "type": "choice",
        "options": ["신용카드", "계좌이체", "간편결제"]
      },
      "next_step": {
        "default": "confirm_order"
      }
    },
    {
      "step_id": "confirm_order",
      "step_name": "주문 확인",
      "prompt": "주문을 확정하시겠습니까? 총 금액은 {total_price}원입니다.",
      "actions": [
        {
          "type": "tts",
          "text": "주문을 확정하시겠습니까? 총 금액은 {total_price}원입니다."
        }
      ],
      "required_fields": [],
      "validation": {
        "type": "user_confirmation",
        "options": ["네", "아니오"]
      },
      "next_step": {
        "default": "payment",
        "on_negative": "cancel"
      }
    },
    {
      "step_id": "payment",
      "step_name": "결제 진행",
      "prompt": "결제를 진행합니다.",
      "actions": [
        {
          "type": "tool_call",
          "tool_name": "click_element",
          "arguments": {
            "selector": "#payment-button"
          }
        },
        {
          "type": "ocr",
          "target": "payment_keypad"
        }
      ],
      "required_fields": [],
      "validation": {
        "type": "payment_success"
      },
      "next_step": {
        "default": "complete"
      }
    },
    {
      "step_id": "complete",
      "step_name": "완료",
      "prompt": "주문이 완료되었습니다.",
      "actions": [
        {
          "type": "tts",
          "text": "주문이 완료되었습니다. 주문번호는 {order_id}입니다."
        },
        {
          "type": "backend_notify",
          "endpoint": "/backend/order",
          "data": {
            "order_id": "{order_id}",
            "site": "coupang"
          }
        }
      ],
      "required_fields": [],
      "next_step": null
    },
    {
      "step_id": "cancel",
      "step_name": "취소",
      "prompt": "주문이 취소되었습니다.",
      "actions": [
        {
          "type": "tts",
          "text": "주문을 취소했습니다."
        }
      ],
      "next_step": null
    }
  ],
  "error_handling": {
    "max_retries": 3,
    "timeout": 60,
    "fallback_step": "cancel"
  }
}
```

---

## 플로우 실행 과정

### 1. 플로우 시작

**트리거**: LLM이 `flow_type`을 반환

```python
llm_command = {
    "intent": "checkout",
    "site": "coupang",
    "flow_type": "checkout"
}

# 플로우 엔진 시작
flow = load_flow("coupang_checkout.json")
flow_instance = FlowInstance(flow, session_id)
```

---

### 2. 단계별 실행

```python
for step in flow.steps:
    # 1. TTS 안내
    tts_text = render_template(step.prompt, context)
    await send_tts(tts_text)

    # 2. 액션 실행
    for action in step.actions:
        if action.type == "tool_call":
            await send_tool_call(action)
        elif action.type == "tts":
            await send_tts(action.text)

    # 3. 사용자 입력 대기
    if step.required_fields:
        user_input = await wait_for_input(step.required_fields)

        # 4. 검증
        if not validate(user_input, step.validation):
            await send_error("입력이 올바르지 않습니다.")
            continue  # 재시도

    # 5. 다음 단계로
    next_step_id = determine_next_step(step, user_input)
    if next_step_id is None:
        break  # 완료 또는 취소
```

---

## 액션 타입

### 1. `tts` - TTS 안내

```json
{
  "type": "tts",
  "text": "배송지 주소를 말씀해주세요."
}
```

### 2. `tool_call` - MCP 도구 호출

```json
{
  "type": "tool_call",
  "tool_name": "navigate_to_url",
  "arguments": {
    "url": "https://www.coupang.com/cart"
  }
}
```

### 3. `ocr` - OCR 실행

```json
{
  "type": "ocr",
  "target": "payment_keypad"
}
```

### 4. `backend_notify` - 백엔드 서버 알림

```json
{
  "type": "backend_notify",
  "endpoint": "/backend/order",
  "data": {
    "order_id": "{order_id}",
    "site": "coupang"
  }
}
```

---

## 검증 타입

### 1. `user_confirmation` - 예/아니오 확인

```json
{
  "type": "user_confirmation",
  "options": ["네", "아니오", "예", "확인", "취소"]
}
```

### 2. `choice` - 선택지

```json
{
  "type": "choice",
  "options": ["신용카드", "계좌이체", "간편결제"]
}
```

### 3. `address` - 주소 형식

```json
{
  "type": "address",
  "fields": {
    "address": {
      "min_length": 10,
      "pattern": "^[가-힣0-9\\s-]+$"
    }
  }
}
```

### 4. `phone` - 전화번호 형식

```json
{
  "type": "phone",
  "pattern": "^010-\\d{4}-\\d{4}$"
}
```

### 5. `payment_success` - 결제 성공 확인

```json
{
  "type": "payment_success",
  "check_element": "#order-complete"
}
```

---

## 템플릿 변수

플로우 프롬프트에서 사용 가능한 변수:

```python
{
  "item_count": 3,
  "total_price": 15000,
  "order_id": "ORD123456",
  "address": "서울시 강남구...",
  "phone": "010-1234-5678",
  "payment_method": "신용카드"
}
```

**사용 예시**:
```json
{
  "prompt": "총 금액은 {total_price}원입니다."
}
```

---

## 에러 처리

### 재시도 로직

```json
{
  "error_handling": {
    "max_retries": 3,
    "timeout": 60,
    "fallback_step": "cancel"
  }
}
```

### 에러 타입별 처리

**타임아웃**:
```python
if time.time() - step_start > step.timeout:
    await send_error("시간이 초과되었습니다.")
    goto(fallback_step)
```

**검증 실패**:
```python
retry_count = 0
while retry_count < max_retries:
    user_input = await wait_for_input()
    if validate(user_input):
        break
    retry_count += 1
    await send_tts("다시 입력해주세요.")
```

---

## 사이트별 플로우 예시

### 쿠팡 검색 플로우

```json
{
  "flow_id": "coupang_search",
  "flow_type": "search",
  "site": "coupang",
  "steps": [
    {
      "step_id": "navigate",
      "actions": [
        {
          "type": "tool_call",
          "tool_name": "navigate_to_url",
          "arguments": {"url": "https://www.coupang.com"}
        }
      ],
      "next_step": {"default": "search_input"}
    },
    {
      "step_id": "search_input",
      "actions": [
        {
          "type": "tool_call",
          "tool_name": "fill_input",
          "arguments": {
            "selector": "#searchKeyword",
            "value": "{keyword}"
          }
        },
        {
          "type": "tool_call",
          "tool_name": "click_element",
          "arguments": {"selector": "#searchBtn"}
        }
      ],
      "next_step": {"default": "extract_results"}
    },
    {
      "step_id": "extract_results",
      "actions": [
        {
          "type": "tool_call",
          "tool_name": "get_text",
          "arguments": {"selector": ".product-list"}
        }
      ],
      "next_step": null
    }
  ]
}
```

---

### 네이버 회원가입 플로우

```json
{
  "flow_id": "naver_signup",
  "flow_type": "signup",
  "site": "naver",
  "steps": [
    {
      "step_id": "email_input",
      "prompt": "이메일 주소를 말씀해주세요.",
      "required_fields": ["email"],
      "validation": {
        "type": "email",
        "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
      },
      "next_step": {"default": "password_input"}
    },
    {
      "step_id": "password_input",
      "prompt": "비밀번호를 입력해주세요. 8자 이상, 영문과 숫자를 포함해야 합니다.",
      "required_fields": ["password"],
      "validation": {
        "type": "password",
        "min_length": 8,
        "require_digit": true,
        "require_alpha": true
      },
      "next_step": {"default": "phone_verification"}
    },
    {
      "step_id": "phone_verification",
      "prompt": "본인 인증을 위해 휴대폰 번호를 입력해주세요.",
      "actions": [
        {
          "type": "tool_call",
          "tool_name": "fill_input",
          "arguments": {
            "selector": "#phone",
            "value": "{phone}"
          }
        },
        {
          "type": "tool_call",
          "tool_name": "click_element",
          "arguments": {"selector": "#send-sms"}
        }
      ],
      "required_fields": ["phone", "verification_code"],
      "next_step": {"default": "complete"}
    }
  ]
}
```

---

## 플로우 개발 가이드

### 1. JSON 파일 작성

```bash
AI/app/flows/사이트명/플로우타입.json
```

**예시**:
```
AI/app/flows/coupang/checkout.json
AI/app/flows/naver/signup.json
AI/app/flows/elevenst/search.json
```

---

### 2. 스키마 검증

```python
from pydantic import BaseModel, ValidationError

class FlowStep(BaseModel):
    step_id: str
    step_name: str
    prompt: str
    actions: list
    required_fields: list
    validation: dict
    next_step: dict

class Flow(BaseModel):
    flow_id: str
    flow_type: str
    site: str
    version: str
    steps: list[FlowStep]
    error_handling: dict

# 검증
flow_data = load_json("coupang_checkout.json")
flow = Flow(**flow_data)
```

---

### 3. 테스트

```python
# tests/test_flow_engine.py
import pytest
from app.services.flow_engine import FlowEngine

def test_coupang_checkout():
    engine = FlowEngine()
    flow = engine.load_flow("coupang_checkout")

    # 플로우 시작
    session = engine.start_flow(flow, session_id="test_123")

    # 단계별 실행
    current_step = session.get_current_step()
    assert current_step.step_id == "start"

    # 사용자 입력 시뮬레이션
    session.provide_input("네")
    current_step = session.next_step()
    assert current_step.step_id == "address_input"
```

---

## 플로우 상태 관리

### 플로우 인스턴스

```python
class FlowInstance:
    def __init__(self, flow: Flow, session_id: str):
        self.flow = flow
        self.session_id = session_id
        self.current_step_index = 0
        self.context = {}  # 템플릿 변수
        self.retry_count = 0
        self.created_at = datetime.now()

    def get_current_step(self):
        return self.flow.steps[self.current_step_index]

    def next_step(self, next_step_id: str = None):
        if next_step_id:
            # 특정 단계로 이동
            for i, step in enumerate(self.flow.steps):
                if step.step_id == next_step_id:
                    self.current_step_index = i
                    return step
        else:
            # 순차적 이동
            self.current_step_index += 1
            if self.current_step_index >= len(self.flow.steps):
                return None
            return self.flow.steps[self.current_step_index]
```

---

## 참고

- JSON Schema: https://json-schema.org/
- Pydantic: https://docs.pydantic.dev/
- State Machine Pattern: https://refactoring.guru/design-patterns/state
