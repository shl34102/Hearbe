# MCP 데스크탑 앱 (Desktop App)

시각장애인을 위한 음성 기반 웹 쇼핑 지원 데스크탑 애플리케이션

## 📋 목차

- [프로젝트 개요](#-프로젝트-개요)
- [아키텍처](#-아키텍처)
- [모듈 구조](#-모듈-구조)
- [시작하기](#-시작하기)
- [개발 가이드](#-개발-가이드)
- [팀 협업](#-팀-협업)
- [기술 스택](#-기술-스택)

## 🎯 프로젝트 개요

### 주요 기능

- **음성 명령 인터페이스**: V키 핫키로 음성 명령 녹음
- **브라우저 자동화**: Chrome CDP를 통한 웹 쇼핑 자동화
- **MCP 서버 통합**: Playwright 기반 브라우저 제어
- **실시간 서버 통신**: WebSocket을 통한 STT/LLM/TTS 처리
- **최소 UI**: 시스템 트레이 아이콘 및 상태 표시

### 워크플로우

```
1. 사용자 V키 누름 → 녹음 시작
2. 음성 명령 입력 → STT 변환 (서버)
3. LLM 명령 생성 → MCP 도구 호출
4. 브라우저 자동화 실행 → 결과 반환
5. TTS 음성 안내 → 재생
```

## 🏗 아키텍처

### 이벤트 기반 아키텍처

모든 모듈은 **중앙 이벤트 버스**를 통해 통신합니다.

```
┌─────────────────────────────────────────────────────────┐
│                   중앙 이벤트 버스                         │
│          (Event Bus - Publish/Subscribe)                │
└─────────────────────────────────────────────────────────┘
         ▲         ▲         ▲         ▲         ▲
         │         │         │         │         │
    ┌────┴───┐ ┌──┴────┐ ┌──┴────┐ ┌──┴─────┐ ┌┴──────┐
    │ Audio  │ │Browser│ │  MCP  │ │Network │ │Session│
    │ 모듈   │ │ 모듈  │ │ 모듈  │ │ 모듈   │ │ 모듈  │
    └────────┘ └───────┘ └───────┘ └────────┘ └───────┘
         │                                           │
         └─────────────┐                 ┌──────────┘
                       ▼                 ▼
                   ┌───────────────────────┐
                   │      UI 모듈          │
                   │  (시스템 트레이)      │
                   └───────────────────────┘
```

### 주요 이벤트 흐름

```
HOTKEY_PRESSED → RECORDING_STARTED → RECORDING_STOPPED → AUDIO_READY
    → STT_RESULT_RECEIVED → LLM_COMMAND_RECEIVED → MCP_TOOL_CALL
    → MCP_RESULT → TTS_AUDIO_RECEIVED → TTS_PLAYBACK_FINISHED
```

## 📁 모듈 구조

```
MCP/
├── core/                      # 핵심 공통 모듈
│   ├── event_bus.py          # ✅ 중앙 이벤트 버스
│   ├── interfaces.py         # ✅ 모듈 인터페이스 정의
│   └── config.py             # ✅ 설정 관리
│
├── audio/                     # 담당자 A
│   ├── hotkey.py             # V키 핫키 처리
│   ├── recorder.py           # 마이크 녹음
│   ├── player.py             # TTS 재생
│   └── tests/
│
├── browser/                   # 담당자 B
│   ├── launcher.py           # Chrome 실행
│   ├── cdp_client.py         # CDP 연결
│   └── tests/
│
├── mcp/                       # 담당자 C
│   ├── server_manager.py     # MCP 서버 관리
│   ├── client.py             # MCP 클라이언트
│   ├── playwright_mcp_server.py  # Playwright 도구
│   └── tests/
│
├── network/                   # 담당자 A 또는 B
│   ├── ws_client.py          # WebSocket 클라이언트
│   ├── auth.py               # 인증 처리
│   └── tests/
│
├── session/                   # 담당자 C
│   ├── state_manager.py      # 세션 상태 관리
│   └── tests/
│
├── ui/                        # 담당자 A 또는 B
│   ├── tray_icon.py          # 시스템 트레이
│   ├── mini_window.py        # 최소 UI
│   └── tests/
│
├── main.py                    # ✅ 앱 진입점
├── requirements.txt           # ✅ 의존성
├── .env.example              # ✅ 환경 변수 예시
└── README.md                 # ✅ 이 문서
```

**범례:**
- ✅ 완료된 파일
- (비어있음) 구현 필요

## 🚀 시작하기

### 1. 의존성 설치

```bash
# Python 3.9 이상 필요
cd MCP
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 2. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 수정 (필요 시)
# - 서버 URL
# - Chrome 경로 등
```

### 3. 실행

```bash
python main.py
```

## 👨‍💻 개발 가이드

### 모듈 개발 순서

1. **`core/interfaces.py`에서 인터페이스 확인**
   - 각 모듈이 구현해야 할 인터페이스가 정의되어 있습니다.

2. **인터페이스 구현**
   ```python
   from core.interfaces import IAudioRecorder

   class AudioRecorder(IAudioRecorder):
       def start_recording(self) -> None:
           # 구현
           pass
   ```

3. **이벤트 발행/구독**
   ```python
   from core.event_bus import subscribe, publish, EventType, Event

   # 이벤트 구독
   def on_hotkey_pressed(event: Event):
       print(f"Hotkey pressed: {event.data}")

   subscribe(EventType.HOTKEY_PRESSED, on_hotkey_pressed)

   # 이벤트 발행
   await publish(EventType.RECORDING_STARTED, data=None, source="audio")
   ```

4. **`main.py`에 모듈 통합**
   ```python
   # setup_modules() 메서드에서 초기화
   from audio.recorder import AudioRecorder
   self.audio_recorder = AudioRecorder()
   ```

### 단위 테스트 작성

```python
# audio/tests/test_recorder.py
import pytest
from audio.recorder import AudioRecorder

def test_recording():
    recorder = AudioRecorder()
    recorder.start_recording()
    assert recorder.is_recording()
```

실행:
```bash
pytest audio/tests/
```

## 🤝 팀 협업

### Git 브랜치 전략

```
main
  └── develop
      ├── feature/audio-module      (담당자 A)
      ├── feature/browser-module    (담당자 B)
      ├── feature/mcp-module        (담당자 C)
      ├── feature/network-module    (담당자 A)
      └── feature/ui-module         (담당자 B)
```

### 작업 규칙

1. **모듈별 폴더 분리**: 각자 담당 모듈 폴더에서만 작업
2. **공통 파일 주의**: `core/` 수정 시 팀에 공지
3. **인터페이스 우선**: 다른 모듈 기능이 필요하면 인터페이스에 추가
4. **이벤트 기반 통신**: 직접 호출 대신 이벤트 사용

### 커밋 컨벤션

```
feat(audio): V키 핫키 기능 구현
fix(browser): Chrome 실행 오류 수정
docs(readme): 설치 가이드 추가
test(network): WebSocket 연결 테스트 추가
```

### Pull Request

```markdown
## 변경 사항
- V키 핫키 감지 기능 구현
- 마이크 녹음 기능 구현

## 테스트
- [x] 단위 테스트 통과
- [x] 수동 테스트 완료

## 관련 이슈
#12
```

## 🛠 기술 스택

### 핵심 라이브러리

- **pyaudio**: 오디오 녹음/재생
- **pynput**: 핫키 처리
- **websockets**: WebSocket 통신
- **playwright**: 브라우저 자동화
- **pystray**: 시스템 트레이 UI

### 개발 도구

- **pytest**: 테스트 프레임워크
- **black**: 코드 포매터
- **flake8**: 코드 린터
- **mypy**: 타입 체커

### 배포

- **PyInstaller**: .exe 패키징

## 📝 개발 현황

### Phase 1: 기반 구조 (완료 ✅)

- [x] 프로젝트 폴더 구조
- [x] 이벤트 버스 (`core/event_bus.py`)
- [x] 인터페이스 정의 (`core/interfaces.py`)
- [x] 설정 관리 (`core/config.py`)
- [x] 의존성 파일 (`requirements.txt`)
- [x] 환경 변수 예시 (`.env.example`)
- [x] 메인 진입점 (`main.py`)

### Phase 2: 모듈별 개발 (진행 중 🚧)

**담당자별 작업:**

#### 담당자 A: Audio + Network
- [ ] `audio/hotkey.py` - V키 핫키
- [ ] `audio/recorder.py` - 마이크 녹음
- [ ] `audio/player.py` - TTS 재생
- [ ] `network/ws_client.py` - WebSocket 클라이언트
- [ ] `network/auth.py` - 인증

#### 담당자 B: Browser + UI
- [ ] `browser/launcher.py` - Chrome 실행
- [ ] `browser/cdp_client.py` - CDP 연결
- [ ] `ui/tray_icon.py` - 시스템 트레이 (미구현)
- [x] `ui/mini_window.py` - 최소 UI ✅
- [x] `ui/ui_manager.py` - UI 관리자 ✅

#### 담당자 C: MCP + Session
- [ ] `mcp/server_manager.py` - MCP 서버 관리
- [ ] `mcp/playwright_mcp_server.py` - Playwright 도구
- [ ] `mcp/client.py` - MCP 클라이언트
- [ ] `session/state_manager.py` - 세션 관리

### Phase 3: 통합 (예정 📅)

- [ ] 모듈 통합
- [ ] 전체 플로우 테스트
- [ ] 버그 수정

### Phase 4: 배포 (예정 📅)

- [ ] PyInstaller 설정
- [ ] .exe 빌드
- [ ] 설치 가이드

## 🔍 참고 자료

### 공식 문서

- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [Playwright Python](https://playwright.dev/python/)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/)

### 내부 문서

- [전체 기획 문서](../docs/plan%20docs.md)
- [AI 서버 설계](../AI/README.md)
- [구현 계획](../../../.claude/plans/modular-splashing-cerf.md)

### 협업 문서

- **[팀 역할 분담 및 일정](docs/TEAM_ASSIGNMENT.md)** ⭐ - 2인 개발 계획 (3주)
- [이벤트 명세서](docs/EVENT_SPECIFICATION.md) - 모듈 간 통신 이벤트 정의
- [모듈 통합 가이드](docs/INTEGRATION_GUIDE.md) - main.py 통합 방법
- [환경 변수 명세서](docs/ENV_SPECIFICATION.md) - .env 설정 가이드
- [클라이언트 설정 가이드](docs/MCP_CLIENT_SETUP_GUIDE.md) - 개발/배포 설정
