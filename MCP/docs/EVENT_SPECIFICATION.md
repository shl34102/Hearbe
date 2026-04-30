# 이벤트 명세서 (Event Specification)

> MCP 데스크탑 앱의 모듈 간 통신을 위한 이벤트 정의

## 개요

모든 모듈은 **이벤트 버스**를 통해 통신합니다. 직접 함수 호출 대신 이벤트 발행/구독 패턴을 사용하여 모듈 간 결합도를 최소화합니다.

## 이벤트 발행/구독 방법

### 이벤트 발행

```python
from core.event_bus import publish, EventType, Event

# 데이터 없이 발행
await publish(EventType.HOTKEY_PRESSED, source="audio.hotkey")

# 데이터와 함께 발행
await publish(
    EventType.AUDIO_READY,
    source="audio.recorder",
    data=audio_bytes
)
```

### 이벤트 구독

```python
from core.event_bus import subscribe, EventType, Event

def my_handler(event: Event):
    print(f"Received: {event.type}, Data: {event.data}")

# 핸들러 등록
subscribe(EventType.RECORDING_STARTED, my_handler)
```

## 이벤트 타입 정의

### 1. HOTKEY_PRESSED

**설명**: V키 핫키가 눌렸을 때

**발행자**: `audio.hotkey.HotkeyManager`

**구독자**: `ui.ui_manager.UIManager`, `audio.recorder.AudioRecorder`

**데이터**: 없음

**예시**:
```python
await publish(EventType.HOTKEY_PRESSED, source="audio.hotkey")
```

---

### 2. RECORDING_STARTED

**설명**: 마이크 녹음이 시작되었을 때

**발행자**: `audio.recorder.AudioRecorder`

**구독자**: `ui.ui_manager.UIManager`, `session.state_manager.SessionManager`

**데이터**: 없음

**예시**:
```python
await publish(EventType.RECORDING_STARTED, source="audio.recorder")
```

---

### 3. RECORDING_STOPPED

**설명**: 마이크 녹음이 종료되었을 때

**발행자**: `audio.recorder.AudioRecorder`

**구독자**: `ui.ui_manager.UIManager`, `session.state_manager.SessionManager`

**데이터**: 없음

**예시**:
```python
await publish(EventType.RECORDING_STOPPED, source="audio.recorder")
```

---

### 4. AUDIO_READY

**설명**: 녹음된 오디오 데이터가 준비되었을 때

**발행자**: `audio.recorder.AudioRecorder`

**구독자**: `network.ws_client.WebSocketClient`

**데이터 타입**: `bytes`

**데이터 형식**: WAV 또는 PCM 오디오 바이트

**예시**:
```python
audio_data = recorder.get_audio()
await publish(
    EventType.AUDIO_READY,
    source="audio.recorder",
    data=audio_data
)
```

---

### 5. STT_RESULT_RECEIVED

**설명**: 서버로부터 STT(음성→텍스트) 결과를 받았을 때

**발행자**: `network.ws_client.WebSocketClient`

**구독자**: `ui.ui_manager.UIManager`, `session.state_manager.SessionManager`

**데이터 타입**: `str`

**데이터 형식**: 인식된 텍스트

**예시**:
```python
await publish(
    EventType.STT_RESULT_RECEIVED,
    source="network.ws_client",
    data="쿠팡에서 우유 검색해줘"
)
```

---

### 6. LLM_COMMAND_RECEIVED

**설명**: 서버로부터 LLM이 해석한 명령을 받았을 때

**발행자**: `network.ws_client.WebSocketClient`

**구독자**: `session.state_manager.SessionManager`

**데이터 타입**: `dict`

**데이터 형식**:
```python
{
    "intent": "search_product",
    "parameters": {
        "site": "coupang",
        "keyword": "우유"
    }
}
```

**예시**:
```python
await publish(
    EventType.LLM_COMMAND_RECEIVED,
    source="network.ws_client",
    data={
        "intent": "search_product",
        "parameters": {"site": "coupang", "keyword": "우유"}
    }
)
```

---

### 7. MCP_TOOL_CALL

**설명**: MCP 도구 호출 요청 (서버로부터 받음)

**발행자**: `network.ws_client.WebSocketClient`

**구독자**: `mcp.client.MCPClient`

**데이터 타입**: `dict`

**데이터 형식**:
```python
{
    "tool_id": "navigate",
    "tool_name": "navigate_to_url",
    "arguments": {
        "url": "https://www.coupang.com"
    },
    "request_id": "req_12345"
}
```

**예시**:
```python
await publish(
    EventType.MCP_TOOL_CALL,
    source="network.ws_client",
    data={
        "tool_id": "navigate",
        "tool_name": "navigate_to_url",
        "arguments": {"url": "https://www.coupang.com"},
        "request_id": "req_12345"
    }
)
```

---

### 8. MCP_RESULT

**설명**: MCP 도구 실행 결과

**발행자**: `mcp.client.MCPClient`

**구독자**: `network.ws_client.WebSocketClient`

**데이터 타입**: `dict`

**데이터 형식**:
```python
{
    "request_id": "req_12345",
    "success": True,
    "result": {
        "status": "navigated",
        "url": "https://www.coupang.com"
    },
    "error": None  # 실패 시 에러 메시지
}
```

**예시**:
```python
await publish(
    EventType.MCP_RESULT,
    source="mcp.client",
    data={
        "request_id": "req_12345",
        "success": True,
        "result": {"status": "navigated", "url": "https://www.coupang.com"},
        "error": None
    }
)
```

---

### 9. TTS_AUDIO_RECEIVED

**설명**: 서버로부터 TTS(텍스트→음성) 오디오를 받았을 때

**발행자**: `network.ws_client.WebSocketClient`

**구독자**: `audio.player.AudioPlayer`

**데이터 타입**: `bytes`

**데이터 형식**: MP3 또는 WAV 오디오 바이트

**예시**:
```python
await publish(
    EventType.TTS_AUDIO_RECEIVED,
    source="network.ws_client",
    data=tts_audio_bytes
)
```

---

### 10. TTS_PLAYBACK_FINISHED

**설명**: TTS 오디오 재생이 완료되었을 때

**발행자**: `audio.player.AudioPlayer`

**구독자**: `ui.ui_manager.UIManager`, `session.state_manager.SessionManager`

**데이터**: 없음

**예시**:
```python
await publish(
    EventType.TTS_PLAYBACK_FINISHED,
    source="audio.player"
)
```

---

### 11. BROWSER_READY

**설명**: Chrome 브라우저가 실행되고 CDP 연결이 완료되었을 때

**발행자**: `browser.launcher.BrowserController`

**구독자**: `mcp.server_manager.MCPServerManager`

**데이터 타입**: `dict`

**데이터 형식**:
```python
{
    "cdp_url": "ws://127.0.0.1:9222/devtools/browser/...",
    "process_id": 12345
}
```

**예시**:
```python
await publish(
    EventType.BROWSER_READY,
    source="browser.launcher",
    data={
        "cdp_url": "ws://127.0.0.1:9222/devtools/browser/xxx",
        "process_id": 12345
    }
)
```

---

### 12. MCP_SERVER_READY

**설명**: MCP 서버 프로세스가 시작되고 준비되었을 때

**발행자**: `mcp.server_manager.MCPServerManager`

**구독자**: `mcp.client.MCPClient`

**데이터 타입**: `dict`

**데이터 형식**:
```python
{
    "server_url": "stdio://mcp-server",
    "available_tools": ["navigate_to_url", "click_element", "fill_input"]
}
```

**예시**:
```python
await publish(
    EventType.MCP_SERVER_READY,
    source="mcp.server_manager",
    data={
        "server_url": "stdio://mcp-server",
        "available_tools": ["navigate_to_url", "click_element", "fill_input"]
    }
)
```

---

### 13. SESSION_UPDATED

**설명**: 세션 상태가 업데이트되었을 때

**발행자**: `session.state_manager.SessionManager`

**구독자**: `ui.ui_manager.UIManager`

**데이터 타입**: `dict`

**데이터 형식**:
```python
{
    "current_site": "coupang",
    "current_task": "searching",
    "last_query": "우유"
}
```

**예시**:
```python
await publish(
    EventType.SESSION_UPDATED,
    source="session.state_manager",
    data={
        "current_site": "coupang",
        "current_task": "searching",
        "last_query": "우유"
    }
)
```

---

### 14. ERROR_OCCURRED

**설명**: 모듈에서 오류가 발생했을 때

**발행자**: 모든 모듈

**구독자**: `ui.ui_manager.UIManager`, `session.state_manager.SessionManager`

**데이터 타입**: `str` 또는 `dict`

**데이터 형식**:
```python
# 간단한 경우
"WebSocket connection failed"

# 상세한 경우
{
    "module": "network.ws_client",
    "error_type": "ConnectionError",
    "message": "Failed to connect to server",
    "details": "Connection timeout after 10s"
}
```

**예시**:
```python
await publish(
    EventType.ERROR_OCCURRED,
    source="network.ws_client",
    data={
        "module": "network.ws_client",
        "error_type": "ConnectionError",
        "message": "Failed to connect to server"
    }
)
```

---

### 15. APP_SHUTDOWN

**설명**: 앱이 종료될 때 (정리 작업 트리거)

**발행자**: `main.MCPApp`

**구독자**: 모든 모듈 (정리 작업 수행)

**데이터**: 없음

**예시**:
```python
await publish(EventType.APP_SHUTDOWN, source="main")
```

---

## 이벤트 흐름 예시

### 음성 명령 전체 플로우

```
1. [Audio] HOTKEY_PRESSED 발행
   → [UI] 상태 업데이트 ("준비")
   → [Audio] 녹음 시작

2. [Audio] RECORDING_STARTED 발행
   → [UI] 상태 업데이트 ("녹음 중")

3. [Audio] RECORDING_STOPPED 발행
   → [UI] 상태 업데이트 ("처리 중")

4. [Audio] AUDIO_READY 발행 (data: audio_bytes)
   → [Network] 서버로 오디오 전송

5. [Network] STT_RESULT_RECEIVED 발행 (data: "쿠팡에서 우유 검색")
   → [UI] 상태 업데이트 ("명령: 쿠팡에서 우유...")

6. [Network] LLM_COMMAND_RECEIVED 발행 (data: {intent, parameters})
   → [Session] 세션 업데이트

7. [Network] MCP_TOOL_CALL 발행 (data: {tool_name, arguments})
   → [MCP] 도구 실행

8. [MCP] MCP_RESULT 발행 (data: {result})
   → [Network] 서버로 결과 전송

9. [Network] TTS_AUDIO_RECEIVED 발행 (data: tts_audio)
   → [Audio] TTS 재생

10. [Audio] TTS_PLAYBACK_FINISHED 발행
    → [UI] 상태 업데이트 ("대기 중")
```

## 주의사항

### 1. 비동기 처리
- 모든 `publish()` 호출은 `await`와 함께 사용
- 이벤트 핸들러는 동기/비동기 모두 가능

### 2. 에러 처리
```python
try:
    await publish(EventType.AUDIO_READY, source="audio", data=audio)
except Exception as e:
    await publish(EventType.ERROR_OCCURRED, source="audio", data=str(e))
```

### 3. 데이터 타입 검증
- 구독자는 받은 데이터의 타입을 항상 검증
```python
def handle_stt_result(event: Event):
    if not isinstance(event.data, str):
        logger.error("Invalid STT result data type")
        return
    text = event.data
    # 처리...
```

### 4. 순환 참조 방지
- A → B → A 형태의 이벤트 체인 금지
- 무한 루프 방지를 위해 이벤트 체인 깊이 제한

## 새로운 이벤트 추가 방법

1. `core/event_bus.py`의 `EventType` enum에 추가
2. 이 문서에 명세 추가
3. 팀에 공지

```python
# core/event_bus.py
class EventType(Enum):
    # 기존 이벤트...
    NEW_EVENT = auto()  # 새로운 이벤트
```

## 참고

- 이벤트 버스 구현: [core/event_bus.py](../core/event_bus.py)
- 인터페이스 정의: [core/interfaces.py](../core/interfaces.py)
