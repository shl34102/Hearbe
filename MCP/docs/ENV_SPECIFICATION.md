# 환경 변수 명세서 (Environment Variables Specification)

> MCP 데스크탑 앱의 모든 환경 변수 정의

## 개요

`.env` 파일을 통해 앱의 설정을 관리합니다. 각 모듈은 필요한 환경 변수를 정의하고 사용합니다.

## .env 파일 생성

```bash
# 프로젝트 루트에서 실행
cd c:\ssafy\공통\MCP
cp .env.example .env

# .env 파일을 에디터로 열어 값 수정
notepad .env
```

## 전체 환경 변수 목록

### Network (네트워크 통신)

#### `WS_URL`
**설명**: WebSocket 서버 URL

**기본값**: `ws://localhost:8000/ws`

**예시**:
```env
# 로컬 개발
WS_URL=ws://localhost:8000/ws

# 개발 서버
WS_URL=wss://dev-api.example.com/ws

# 프로덕션 서버
WS_URL=wss://api.example.com/ws
```

**사용 모듈**: `network.ws_client`

---

#### `WS_RECONNECT_DELAY`
**설명**: WebSocket 재연결 대기 시간 (초)

**기본값**: `5`

**예시**:
```env
WS_RECONNECT_DELAY=5
WS_RECONNECT_DELAY=10  # 느린 네트워크
```

**사용 모듈**: `network.ws_client`

---

#### `WS_MAX_RETRIES`
**설명**: WebSocket 최대 재시도 횟수

**기본값**: `10`

**예시**:
```env
WS_MAX_RETRIES=10
WS_MAX_RETRIES=-1  # 무한 재시도
```

**사용 모듈**: `network.ws_client`

---

### Audio (오디오 녹음/재생)

#### `AUDIO_SAMPLE_RATE`
**설명**: 오디오 샘플링 레이트 (Hz)

**기본값**: `16000`

**예시**:
```env
AUDIO_SAMPLE_RATE=16000  # 음성 인식용
AUDIO_SAMPLE_RATE=44100  # 고품질
```

**사용 모듈**: `audio.recorder`, `audio.player`

---

#### `AUDIO_CHANNELS`
**설명**: 오디오 채널 수 (1=모노, 2=스테레오)

**기본값**: `1`

**예시**:
```env
AUDIO_CHANNELS=1  # 모노 (권장)
AUDIO_CHANNELS=2  # 스테레오
```

**사용 모듈**: `audio.recorder`, `audio.player`

---

#### `AUDIO_CHUNK_SIZE`
**설명**: 오디오 버퍼 크기 (프레임 수)

**기본값**: `1024`

**예시**:
```env
AUDIO_CHUNK_SIZE=1024  # 일반
AUDIO_CHUNK_SIZE=512   # 저지연
```

**사용 모듈**: `audio.recorder`

---

#### `AUDIO_FORMAT`
**설명**: 오디오 포맷 (pyaudio 포맷)

**기본값**: `paInt16`

**예시**:
```env
AUDIO_FORMAT=paInt16  # 16-bit PCM
```

**사용 모듈**: `audio.recorder`

---

#### `HOTKEY`
**설명**: 녹음 시작 핫키

**기본값**: `v`

**예시**:
```env
HOTKEY=v
HOTKEY=ctrl+v
HOTKEY=alt+v
```

**사용 모듈**: `audio.hotkey`

---

### Browser (브라우저 제어)

#### `BROWSER_EXECUTABLE_PATH`
**설명**: Chrome 실행 파일 경로 (비어있으면 자동 탐지)

**기본값**: (비어있음)

**예시**:
```env
# Windows
BROWSER_EXECUTABLE_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe

# macOS
BROWSER_EXECUTABLE_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome

# Linux
BROWSER_EXECUTABLE_PATH=/usr/bin/google-chrome
```

**사용 모듈**: `browser.launcher`

---

#### `BROWSER_CDP_PORT`
**설명**: Chrome DevTools Protocol 포트

**기본값**: `9222`

**예시**:
```env
BROWSER_CDP_PORT=9222
BROWSER_CDP_PORT=9223  # 포트 충돌 시
```

**사용 모듈**: `browser.launcher`, `browser.cdp_client`

---

#### `BROWSER_USER_DATA_DIR`
**설명**: Chrome 사용자 데이터 디렉토리 (프로필 저장 위치)

**기본값**: `./chrome_profile`

**예시**:
```env
BROWSER_USER_DATA_DIR=./chrome_profile
BROWSER_USER_DATA_DIR=C:\Users\SSAFY\MCP\chrome_profile
```

**사용 모듈**: `browser.launcher`

---

#### `BROWSER_HEADLESS`
**설명**: 헤드리스 모드 (창 없이 실행)

**기본값**: `false`

**예시**:
```env
BROWSER_HEADLESS=false  # 창 표시 (권장)
BROWSER_HEADLESS=true   # 창 숨김
```

**사용 모듈**: `browser.launcher`

---

### MCP (Model Context Protocol)

#### `MCP_SERVER_COMMAND`
**설명**: MCP 서버 실행 명령어

**기본값**: `python mcp/playwright_mcp_server.py`

**예시**:
```env
MCP_SERVER_COMMAND=python mcp/playwright_mcp_server.py
MCP_SERVER_COMMAND=node mcp_server.js  # Node.js 서버
```

**사용 모듈**: `mcp.server_manager`

---

#### `MCP_SERVER_TIMEOUT`
**설명**: MCP 서버 시작 대기 시간 (초)

**기본값**: `10`

**예시**:
```env
MCP_SERVER_TIMEOUT=10
MCP_SERVER_TIMEOUT=30  # 느린 시스템
```

**사용 모듈**: `mcp.server_manager`

---

#### `MCP_TOOL_TIMEOUT`
**설명**: MCP 도구 실행 최대 대기 시간 (초)

**기본값**: `60`

**예시**:
```env
MCP_TOOL_TIMEOUT=60
MCP_TOOL_TIMEOUT=120  # 복잡한 작업
```

**사용 모듈**: `mcp.client`

---

### Session (세션 관리)

#### `SESSION_FILE_PATH`
**설명**: 세션 저장 파일 경로

**기본값**: `./session.json`

**예시**:
```env
SESSION_FILE_PATH=./session.json
SESSION_FILE_PATH=C:\Users\SSAFY\MCP\session.json
```

**사용 모듈**: `session.state_manager`

---

#### `SESSION_AUTO_SAVE`
**설명**: 세션 자동 저장 여부

**기본값**: `true`

**예시**:
```env
SESSION_AUTO_SAVE=true
SESSION_AUTO_SAVE=false
```

**사용 모듈**: `session.state_manager`

---

### Logging (로깅)

#### `LOG_LEVEL`
**설명**: 로그 레벨

**기본값**: `INFO`

**가능한 값**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**예시**:
```env
LOG_LEVEL=DEBUG  # 개발 시
LOG_LEVEL=INFO   # 일반
LOG_LEVEL=ERROR  # 프로덕션
```

**사용 모듈**: 모든 모듈

---

#### `LOG_FILE_PATH`
**설명**: 로그 파일 경로

**기본값**: `./logs/app.log`

**예시**:
```env
LOG_FILE_PATH=./logs/app.log
LOG_FILE_PATH=C:\Users\SSAFY\MCP\logs\app.log
```

**사용 모듈**: 모든 모듈

---

#### `LOG_MAX_BYTES`
**설명**: 로그 파일 최대 크기 (바이트)

**기본값**: `10485760` (10MB)

**예시**:
```env
LOG_MAX_BYTES=10485760  # 10MB
LOG_MAX_BYTES=52428800  # 50MB
```

**사용 모듈**: 모든 모듈

---

#### `LOG_BACKUP_COUNT`
**설명**: 로그 파일 백업 개수

**기본값**: `5`

**예시**:
```env
LOG_BACKUP_COUNT=5
LOG_BACKUP_COUNT=10
```

**사용 모듈**: 모든 모듈

---

### Debug (디버그)

#### `DEBUG_CONSOLE_ENABLED`
**설명**: 콘솔 입력 모드 활성화 (테스트용)

**기본값**: `false`

**예시**:
```env
DEBUG_CONSOLE_ENABLED=false  # 비활성화
DEBUG_CONSOLE_ENABLED=true   # 활성화
```

**사용 모듈**: `debug.console_input`

---

## 환경별 설정 예시

### 개발 환경 (.env.development)

```env
# Network
WS_URL=ws://localhost:8000/ws
WS_RECONNECT_DELAY=5
WS_MAX_RETRIES=10

# Audio
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_CHUNK_SIZE=1024
HOTKEY=v

# Browser
BROWSER_EXECUTABLE_PATH=
BROWSER_CDP_PORT=9222
BROWSER_USER_DATA_DIR=./chrome_profile
BROWSER_HEADLESS=false

# MCP
MCP_SERVER_COMMAND=python mcp/playwright_mcp_server.py
MCP_SERVER_TIMEOUT=10
MCP_TOOL_TIMEOUT=60

# Session
SESSION_FILE_PATH=./session.json
SESSION_AUTO_SAVE=true

# Logging
LOG_LEVEL=DEBUG
LOG_FILE_PATH=./logs/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# Debug
DEBUG_CONSOLE_ENABLED=true
```

### 프로덕션 환경 (.env.production)

```env
# Network
WS_URL=wss://api.example.com/ws
WS_RECONNECT_DELAY=10
WS_MAX_RETRIES=-1

# Audio
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_CHUNK_SIZE=1024
HOTKEY=v

# Browser
BROWSER_EXECUTABLE_PATH=
BROWSER_CDP_PORT=9222
BROWSER_USER_DATA_DIR=C:\ProgramData\MCPApp\chrome_profile
BROWSER_HEADLESS=false

# MCP
MCP_SERVER_COMMAND=python mcp/playwright_mcp_server.py
MCP_SERVER_TIMEOUT=30
MCP_TOOL_TIMEOUT=120

# Session
SESSION_FILE_PATH=C:\ProgramData\MCPApp\session.json
SESSION_AUTO_SAVE=true

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=C:\ProgramData\MCPApp\logs\app.log
LOG_MAX_BYTES=52428800
LOG_BACKUP_COUNT=10

# Debug
DEBUG_CONSOLE_ENABLED=false
```

## 환경 변수 사용 방법

### 코드에서 환경 변수 읽기

```python
from core.config import get_config

config = get_config()

# Network 설정
ws_url = config.network.ws_url

# Audio 설정
sample_rate = config.audio.sample_rate
hotkey = config.audio.hotkey

# Browser 설정
cdp_port = config.browser.cdp_port

# MCP 설정
server_command = config.mcp.server_command

# Logging 설정
log_level = config.log.level
```

### 타입 안전하게 접근

```python
from core.config import get_config, AudioConfig, BrowserConfig

config = get_config()

# 타입 힌트로 IDE 자동완성 가능
audio_config: AudioConfig = config.audio
print(f"Sample rate: {audio_config.sample_rate}")

browser_config: BrowserConfig = config.browser
print(f"CDP port: {browser_config.cdp_port}")
```

## 새로운 환경 변수 추가 방법

### 1. .env.example 업데이트

```env
# 새로운 설정 추가
MY_NEW_SETTING=default_value
```

### 2. core/config.py 업데이트

```python
from dataclasses import dataclass

@dataclass
class MyModuleConfig:
    my_new_setting: str

@dataclass
class AppConfig:
    # 기존 설정...
    my_module: MyModuleConfig

def get_config() -> AppConfig:
    # .env 로드
    load_dotenv()

    return AppConfig(
        # 기존 설정...
        my_module=MyModuleConfig(
            my_new_setting=os.getenv("MY_NEW_SETTING", "default_value")
        )
    )
```

### 3. 문서 업데이트

이 문서에 새로운 환경 변수 설명 추가

### 4. 팀에 공지

새로운 환경 변수 추가를 팀원들에게 알리기

## 주의사항

### 1. .env 파일은 Git에 커밋하지 마세요

```bash
# .gitignore에 이미 포함됨
.env
.env.*
```

### 2. 민감한 정보는 환경 변수로 관리

```env
# 나쁜 예: 코드에 하드코딩
# ws_url = "ws://secret-server.com/ws"

# 좋은 예: 환경 변수로 관리
WS_URL=ws://secret-server.com/ws
```

### 3. 기본값 제공

```python
# 환경 변수가 없어도 동작하도록 기본값 제공
ws_url = os.getenv("WS_URL", "ws://localhost:8000/ws")
```

## 참고

- 설정 코드: [core/config.py](../core/config.py)
- 환경 변수 예시: [.env.example](../.env.example)
- 통합 가이드: [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
