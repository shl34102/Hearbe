# MCP Client Setup Guide

## 📋 사전 요구사항

- **Windows 10/11**
- **Python 3.11 권장** (패키지 호환성 안정)
- **pip** (Python 패키지 관리자)
- **Git**

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone <repository-url>
cd MCP
```

### 2. 가상 환경 생성 (권장)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/Scripts/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 4. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일을 에디터로 열어 필요한 값 수정
```

주요 설정 항목:

```env
# WebSocket 서버 URL (실제 서버 주소로 변경)
WS_URL=ws://localhost:8000/ws

# 인증 서버 URL
AUTH_URL=http://localhost:8000/auth

# 로그 레벨 (개발 시 DEBUG 권장)
LOG_LEVEL=DEBUG
```

### 5. 실행

```bash
python main.py
```

## 📝 개발 모드

### 코드 포맷팅

```bash
# Black으로 코드 포맷팅
black .

# Flake8으로 코드 검사
flake8 .
```

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 특정 모듈 테스트
pytest audio/tests/

# 커버리지 포함
pytest --cov=.
```

### 타입 체크

```bash
mypy .
```

## 🔧 모듈별 개발 가이드

### Audio 모듈 (담당자 A)

1. `core/interfaces.py`에서 `IAudioRecorder`, `IAudioPlayer`, `IHotkeyManager` 확인
2. `audio/` 폴더에서 구현
3. 테스트 작성: `audio/tests/`

예시:

```python
# audio/hotkey.py
from core.interfaces import IHotkeyManager
from core.event_bus import publish, EventType

class HotkeyManager(IHotkeyManager):
    def register_hotkey(self, key: str, callback):
        # 구현
        pass
```

### Browser 모듈 (담당자 B)

1. `core/interfaces.py`에서 `IBrowserController` 확인
2. `browser/` 폴더에서 구현
3. Chrome CDP 연결 구현

### MCP 모듈 (담당자 C)

1. `core/interfaces.py`에서 `IMCPServerManager`, `IMCPClient` 확인
2. `mcp/` 폴더에서 구현
3. Playwright MCP 서버 구현

### Network 모듈

1. `core/interfaces.py`에서 `IWebSocketClient`, `IAuthManager` 확인
2. `network/` 폴더에서 구현

### Session 모듈

1. `core/interfaces.py`에서 `ISessionManager` 확인
2. `session/` 폴더에서 구현

### UI 모듈

1. `core/interfaces.py`에서 `IUIManager` 확인
2. `ui/` 폴더에서 구현

## 🐛 문제 해결

### Python 모듈을 찾을 수 없음

```bash
# sys.path 확인
python -c "import sys; print('\n'.join(sys.path))"

# 현재 디렉토리를 Python 경로에 추가
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/macOS
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows
```

### PyAudio 설치 오류 (Windows)

```bash
# pip으로 설치 실패 시
pip install pipwin
pipwin install pyaudio
```

### Playwright 오류

```bash
# 브라우저 재설치
playwright install --force chromium
```

## 📦 배포 (Windows onedir 권장)

### PyInstaller로 .exe 생성 (최신 검증됨)

**권장 워크플로우 (onedir)**

이유: Playwright/네이티브 DLL/리소스 경로 문제를 줄이고, 디버깅과 초기 안정성을 확보하기 위함.

1. Windows에서 가상환경 생성 및 의존성 설치
2. Playwright 브라우저 설치
3. PyInstaller onedir 빌드
4. `dist/MCPDesktop/`에서 실행 테스트
5. `.env` 포함 여부 확인 (아래 참고)

**빌드 명령어 (검증 완료)**

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# onedir 빌드
pyinstaller -y --clean --name MCPDesktop --onedir --noconsole --collect-all playwright --add-data ".env;." main.py
```

**실행 위치**

- `dist\MCPDesktop\MCPDesktop.exe`에서 실행
- `.env`는 다음 위치 중 하나에 있어야 함:
  - exe 옆 (`dist\MCPDesktop\.env`) 우선
  - 내부 폴더 (`dist\MCPDesktop\_internal\.env`) 대체

**검증 로그 예시**

- `core.config - INFO - Loaded .env file from ...`
- `audio.audio_manager - INFO - AudioManager initialized with hotkey: space`

> onedir은 배포 폴더 전체를 전달해야 하며, 실행 안정성이 높습니다.

### onefile은 언제?

onefile은 단일 exe 배포에 유리하지만, 실행 시 임시 폴더로 풀리는 구조라
리소스/브라우저/DLL 경로 이슈가 더 자주 발생합니다. 초기 배포 단계에서는
onedir로 안정성을 확보한 뒤 onefile 전환을 권장합니다.

```bash
# (참고) onefile 예시
pyinstaller --onefile --windowed main.py

# dist/ 폴더에 생성됨
```

## ✅ 배포 체크리스트 (Client)

- [ ] `dist\MCPDesktop\` 폴더 그대로 zip 배포
- [ ] `.env` 포함 확인
- [ ] `MCPDesktop.exe` 실행 후 로그에서 `.env` 로드 확인
- [ ] Hotkey가 기대값으로 동작 확인

### 배포 전 체크리스트

- [ ] 모든 테스트 통과
- [ ] .env 파일 확인
- [ ] 로그 레벨을 INFO로 변경
- [ ] 버전 번호 업데이트
- [ ] README 업데이트

## 🤝 Git 워크플로우

### 브랜치 생성

```bash
# develop 브랜치에서 시작
git checkout develop
git pull origin develop

# 기능 브랜치 생성
git checkout -b feature/audio-module
```

### 커밋 및 푸시

```bash
# 변경사항 확인
git status

# 파일 추가
git add audio/hotkey.py
git add audio/tests/test_hotkey.py

# 커밋
git commit -m "feat(audio): V키 핫키 기능 구현"

# 푸시
git push origin feature/audio-module
```

### Pull Request 생성

1. GitHub에서 PR 생성
2. 제목: `feat(audio): V키 핫키 기능 구현`
3. 설명:

   ```markdown
   ## 변경 사항

   - V키 핫키 감지 기능 구현
   - pynput 라이브러리 사용

   ## 테스트

   - [x] 단위 테스트 통과
   - [x] 수동 테스트 완료

   ## 체크리스트

   - [x] 코드 포맷팅 완료 (black)
   - [x] 린팅 통과 (flake8)
   - [x] 테스트 작성
   ```

## 📞 도움말

### 유용한 명령어

```bash
# 의존성 업데이트
pip freeze > requirements.txt

# 프로젝트 구조 확인
tree /F /A  # Windows
tree -L 3   # Linux/macOS

# 로그 실시간 확인
tail -f logs/app.log  # Linux/macOS
Get-Content logs\app.log -Wait  # Windows PowerShell
```

### 추가 리소스

- [Python 공식 문서](https://docs.python.org/)
- [Asyncio 가이드](https://docs.python.org/3/library/asyncio.html)
- [Playwright Python](https://playwright.dev/python/)
- [pynput 문서](https://pynput.readthedocs.io/)

## ⚠️ 주의사항

1. **절대 `.env` 파일을 커밋하지 마세요**
2. **`core/` 폴더 수정 시 팀에 공지**
3. **PR 전에 테스트 실행**
4. **커밋 컨벤션 준수**
5. **각자 담당 모듈 폴더에서만 작업**

---

문제가 발생하면 팀 채널에 문의하거나 이슈를 생성해주세요.
