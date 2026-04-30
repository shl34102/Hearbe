# 모듈 통합 가이드 (Integration Guide)

> 새로운 모듈을 main.py에 통합하는 단계별 가이드

## 개요

각 담당자가 모듈 구현을 완료한 후, `main.py`에 통합하는 방법을 설명합니다.

## 통합 전 체크리스트

- [ ] 모듈이 인터페이스를 구현했는가? ([core/interfaces.py](../core/interfaces.py) 참조)
- [ ] 이벤트 발행/구독이 명세에 맞는가? ([EVENT_SPECIFICATION.md](EVENT_SPECIFICATION.md) 참조)
- [ ] 단위 테스트가 작성되었는가?
- [ ] 환경 변수가 정의되었는가? ([ENV_SPECIFICATION.md](ENV_SPECIFICATION.md) 참조)

## 통합 단계

### 1. main.py에 모듈 import 추가

**위치**: `main.py`의 `setup_modules()` 메서드

**예시 (Audio 모듈 통합)**:

```python
async def setup_modules(self):
    """모듈 초기화 및 설정"""
    logger.info("Setting up modules...")

    # UI 모듈 초기화 (구현 완료)
    from ui.ui_manager import UIManager
    self.ui_manager = UIManager()
    self.ui_manager.setup_event_handlers()
    self.ui_manager.start()

    # Audio 모듈 초기화 (새로 추가) ⭐
    from audio.hotkey import HotkeyManager
    from audio.recorder import AudioRecorder
    from audio.player import AudioPlayer

    self.hotkey_manager = HotkeyManager(self.config.audio.hotkey)
    self.audio_recorder = AudioRecorder(self.config.audio)
    self.audio_player = AudioPlayer()

    self.hotkey_manager.start()
    logger.info("Audio module initialized")

    # 다른 모듈들...
```

### 2. 모듈 초기화 순서 정의

**중요**: 모듈 간 의존성에 따라 초기화 순서가 중요합니다.

#### 권장 순서:

```python
async def setup_modules(self):
    logger.info("Setting up modules...")

    # 1. UI 모듈 (독립적)
    from ui.ui_manager import UIManager
    self.ui_manager = UIManager()
    self.ui_manager.setup_event_handlers()
    self.ui_manager.start()

    # 2. Browser 모듈 (독립적)
    from browser.launcher import BrowserController
    self.browser_controller = BrowserController(self.config.browser)
    await self.browser_controller.launch_chrome()

    # 3. MCP 모듈 (Browser에 의존)
    from mcp.server_manager import MCPServerManager
    from mcp.client import MCPClient

    self.mcp_server_manager = MCPServerManager(self.config.mcp)
    await self.mcp_server_manager.start_server()

    self.mcp_client = MCPClient()
    await self.mcp_client.connect()

    # 4. Audio 모듈 (독립적)
    from audio.hotkey import HotkeyManager
    from audio.recorder import AudioRecorder
    from audio.player import AudioPlayer

    self.hotkey_manager = HotkeyManager(self.config.audio.hotkey)
    self.audio_recorder = AudioRecorder(self.config.audio)
    self.audio_player = AudioPlayer()

    self.hotkey_manager.start()

    # 5. Network 모듈 (모든 모듈이 준비된 후)
    from network.ws_client import WebSocketClient
    from network.auth import AuthManager

    self.auth_manager = AuthManager(self.config.network.auth_url)
    self.ws_client = WebSocketClient(self.config.network.ws_url)
    await self.ws_client.connect()

    # 6. Session 모듈 (모든 모듈이 준비된 후)
    from session.state_manager import SessionManager
    self.session_manager = SessionManager()

    logger.info("All modules initialized successfully")
```

### 3. 모듈 종료 처리 추가

**위치**: `main.py`의 `shutdown()` 메서드

**예시**:

```python
async def shutdown(self):
    """애플리케이션 종료"""
    logger.info("Stopping application...")

    self.running = False

    # 종료 이벤트 발행
    await publish(EventType.APP_SHUTDOWN, source="main")

    # UI 모듈 종료
    if self.ui_manager:
        self.ui_manager.stop()

    # Audio 모듈 종료 (새로 추가) ⭐
    if self.hotkey_manager:
        self.hotkey_manager.stop()

    if self.audio_recorder:
        self.audio_recorder.stop()

    if self.audio_player:
        self.audio_player.stop()

    # Network 모듈 종료
    if self.ws_client:
        await self.ws_client.disconnect()

    # MCP 모듈 종료
    if self.mcp_server_manager:
        await self.mcp_server_manager.stop_server()

    # Browser 모듈 종료
    if self.browser_controller:
        await self.browser_controller.close_chrome()

    logger.info("Application stopped successfully")
```

### 4. 모듈 인스턴스 변수 추가

**위치**: `main.py`의 `__init__()` 메서드

```python
def __init__(self):
    self.config = get_config()

    # 모듈 인스턴스
    self.ui_manager = None
    self.browser_controller = None
    self.mcp_server_manager = None
    self.mcp_client = None
    self.hotkey_manager = None        # 추가 ⭐
    self.audio_recorder = None        # 추가 ⭐
    self.audio_player = None          # 추가 ⭐
    self.ws_client = None
    self.auth_manager = None
    self.session_manager = None

    self.running = False

    logger.info("Application initialized")
```

## 모듈별 통합 예시

### Audio 모듈 (담당자 A)

```python
# main.py - setup_modules() 내

from audio.hotkey import HotkeyManager
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer

self.hotkey_manager = HotkeyManager(self.config.audio.hotkey)
self.audio_recorder = AudioRecorder(self.config.audio)
self.audio_player = AudioPlayer()

self.hotkey_manager.start()
logger.info("Audio module initialized")
```

### Browser 모듈 (담당자 B)

```python
# main.py - setup_modules() 내

from browser.launcher import BrowserController

self.browser_controller = BrowserController(self.config.browser)
await self.browser_controller.launch_chrome()
logger.info("Browser module initialized")
```

### MCP 모듈 (담당자 C)

```python
# main.py - setup_modules() 내

from mcp.server_manager import MCPServerManager
from mcp.client import MCPClient

self.mcp_server_manager = MCPServerManager(self.config.mcp)
await self.mcp_server_manager.start_server()

self.mcp_client = MCPClient()
await self.mcp_client.connect()
logger.info("MCP module initialized")
```

### Network 모듈 (담당자 A 또는 B)

```python
# main.py - setup_modules() 내

from network.ws_client import WebSocketClient
from network.auth import AuthManager

self.auth_manager = AuthManager(self.config.network.auth_url)
self.ws_client = WebSocketClient(self.config.network.ws_url)
await self.ws_client.connect()
logger.info("Network module initialized")
```

### Session 모듈 (담당자 C)

```python
# main.py - setup_modules() 내

from session.state_manager import SessionManager

self.session_manager = SessionManager()
logger.info("Session module initialized")
```

## 통합 후 테스트

### 1. 단독 실행 테스트

```bash
cd c:\ssafy\공통\MCP
python main.py
```

**확인 사항**:
- 모든 모듈이 초기화되는지
- 로그에 에러가 없는지
- UI 창이 정상 표시되는지

### 2. 이벤트 흐름 테스트

**테스트 시나리오**:
1. V키를 눌러 핫키 이벤트 발생
2. 녹음 시작 이벤트 확인
3. V키를 떼어 녹음 종료 이벤트 확인
4. 오디오 데이터 준비 이벤트 확인

**로그 확인**:
```
[INFO] HOTKEY_PRESSED event published
[INFO] RECORDING_STARTED event published
[INFO] RECORDING_STOPPED event published
[INFO] AUDIO_READY event published
```

### 3. 종료 테스트

UI 창의 X 버튼 클릭 후 확인:
- 모든 모듈이 정상 종료되는지
- 프로세스가 완전히 종료되는지
- 좀비 프로세스가 남지 않는지

## 에러 처리

### 모듈 초기화 실패 시

```python
async def setup_modules(self):
    try:
        # Audio 모듈 초기화
        from audio.hotkey import HotkeyManager
        self.hotkey_manager = HotkeyManager(self.config.audio.hotkey)
        self.hotkey_manager.start()
    except Exception as e:
        logger.error(f"Failed to initialize Audio module: {e}", exc_info=True)
        await publish(EventType.ERROR_OCCURRED, source="main", data=str(e))
        # 필수 모듈이면 앱 종료
        raise
```

### 선택적 모듈 처리

```python
# UI는 필수, 시스템 트레이는 선택
try:
    from ui.ui_manager import UIManager
    self.ui_manager = UIManager()
    self.ui_manager.start()
except Exception as e:
    logger.error("UI module is required", exc_info=True)
    raise  # 필수 모듈이므로 앱 종료

try:
    from ui.tray_icon import TrayIcon
    self.tray_icon = TrayIcon()
    self.tray_icon.show()
except Exception as e:
    logger.warning("Tray icon failed, continuing without it", exc_info=True)
    # 선택적 모듈이므로 계속 진행
```

## Git 워크플로우

### 1. 브랜치 생성

```bash
git checkout develop
git pull origin develop
git checkout -b feature/integrate-audio-module
```

### 2. main.py 수정

위 가이드에 따라 `main.py` 수정

### 3. 테스트

```bash
python main.py
```

### 4. 커밋 및 푸시

```bash
git add main.py
git commit -m "feat(integration): Integrate Audio module into main app"
git push origin feature/integrate-audio-module
```

### 5. Pull Request 생성

**PR 제목**: `feat(integration): Integrate Audio module`

**PR 설명**:
```markdown
## 변경 사항
- Audio 모듈을 main.py에 통합
- HotkeyManager, AudioRecorder, AudioPlayer 초기화 추가

## 테스트
- [x] 단독 실행 테스트
- [x] 이벤트 흐름 테스트
- [x] 종료 테스트

## 체크리스트
- [x] 모듈 초기화 순서 확인
- [x] 종료 처리 추가
- [x] 에러 처리 추가
```

## 주의사항

### 1. main.py는 공통 파일
- 여러 담당자가 동시에 수정하면 충돌 가능
- PR 전에 최신 develop 브랜치 머지 필수

```bash
git checkout feature/integrate-audio-module
git pull origin develop
# 충돌 해결 후
git push origin feature/integrate-audio-module
```

### 2. 초기화 순서 중요
- 의존성 있는 모듈은 순서 지켜야 함
- 예: MCP 모듈은 Browser 모듈 이후 초기화

### 3. 비동기 처리
- `async def`로 정의된 메서드는 `await` 필수
- 동기 메서드는 그냥 호출

```python
# 비동기 메서드
await self.ws_client.connect()

# 동기 메서드
self.hotkey_manager.start()
```

## 참고

- 이벤트 명세: [EVENT_SPECIFICATION.md](EVENT_SPECIFICATION.md)
- 환경 변수 명세: [ENV_SPECIFICATION.md](ENV_SPECIFICATION.md)
- 설정 가이드: [MCP_CLIENT_SETUP_GUIDE.md](../MCP_CLIENT_SETUP_GUIDE.md)
