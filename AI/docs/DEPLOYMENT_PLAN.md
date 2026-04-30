# 배포 계획 문서 (A 로컬 ↔ B 배포 서버)

> 처음 합류한 개발자도 전체 맥락을 이해할 수 있도록 작성한 배포 계획서

**버전**: 1.0  
**최종 수정**: 2026-01-27  
**대상**: AI Server(B 배포) + MCP Desktop App(A 로컬)

---

## 1. 요약 (One-page)

- **목표**: 로컬 A에서 음성 입력을 받고, 배포 B에서 ASR/LLM/TTS를 처리한 뒤, MCP 조작용 명령과 TTS를 다시 A로 전달한다.
- **보안 기준**: Google TTS 자격증명은 **B에서만 보관/사용**한다.
- **브라우저 자동화**: **A(로컬)**에서 실행한다. (OCR/HTML 결과도 A에서 생성)
- **핵심 흐름**:
  1) A → B: 음성(PTT) 전송
  2) B: ASR + LLM → tool_calls 생성
  3) B → A: tool_calls 전송
  4) A: MCP 브라우저 자동화 실행 → OCR/HTML 추출
  5) A → B: OCR/HTML 결과 전송
  6) B: 결과 해석 + 응답 문장 생성 + **Google TTS**
  7) B → A: TTS 오디오 스트림/청크 전송

---

## 2. 시스템 구성

### 2.1 역할 분리

| 구분 | 위치 | 역할 |
|------|------|------|
| A (로컬) | 사용자 PC | PTT 녹음, MCP 실행, OCR/HTML 추출, TTS 재생 |
| B (배포) | 서버 | ASR, LLM, 응답 생성, Google TTS |

### 2.2 데이터 흐름

```
[A 로컬]
  음성 PTT 녹음
       │  (audio_chunk)
       ▼
[B 배포] ASR → LLM → tool_calls 생성
       │  (tool_calls)
       ▼
[A 로컬] MCP 실행 → OCR/HTML 추출
       │  (mcp_result: OCR/HTML)
       ▼
[B 배포] 응답 생성 + Google TTS
       │  (tts_chunk)
       ▼
[A 로컬] TTS 재생
```

---

## 3. 배포 환경 (B 서버)

### 3.1 기본 조건
- WSL2 Ubuntu
- GPU: RTX 4050 (CUDA 가능)
- Docker + Docker Compose 설치
- HTTPS 프록시(Nginx + Certbot)

### 3.2 도메인/접속
- **HTTPS**: `https://www.your-ai-server.com`
- **WebSocket**: `wss://www.your-ai-server.com/ws`

---

## 4. 설정 정책

### 4.1 비밀키 관리
- Google TTS 자격증명 파일은 **B 서버에만 위치**
- 로컬 A에는 어떤 클라우드 키도 저장하지 않음

### 4.2 환경변수 기준
- `.env`는 서버에 배포
- `GOOGLE_APPLICATION_CREDENTIALS`는 서버 내부 경로 사용

---

## 5. 배포 절차 (B 서버)

### 5.1 필수 파일 준비
- `AI/.env`
- `AI/config/google-service-account.json`

### 5.2 Docker 실행
```bash
cd ~/S14P11D108/AI
docker compose up -d --build
```

### 5.3 동작 확인
```bash
curl -sS http://localhost:8000/docs | head -n 5
curl -sS https://www.your-ai-server.com/docs | head -n 5
```

---

## 6. 클라이언트(A 로컬) 연동 포인트

- WebSocket 연결 주소는 **B 서버**로 지정
- MCP 결과 전송 시 OCR/HTML을 포함
- TTS는 서버에서 생성되므로 **클라이언트는 재생만 수행**

---

## 7. 클라이언트 환경 변수 (MCP/.env)

클라이언트는 **MCP/.env**만 사용하며, 서버 주소만 배포 주소로 맞추면 됩니다.

```ini
WS_URL=wss://www.your-ai-server.com/ws
AUTH_URL=https://www.your-ai-server.com/auth
```

- `PUBLIC_BASE_URL`은 MCP에서 사용하지 않으면 제거 가능
- 클라이언트에는 API 키/서비스 계정 JSON을 두지 않음

---

## 8. 클라이언트 E2E 테스트 절차

> 목표: A(로컬) ↔ B(배포) 전체 흐름이 끝까지 연결되는지 확인

### 7.1 사전 확인 (B 서버)
```bash
curl -sS https://www.your-ai-server.com/ | head -n 1
wscat -c wss://www.your-ai-server.com/ws
```

### 7.2 클라이언트 설정 (A 로컬)
- HTTP Base URL: `https://www.your-ai-server.com`
- WebSocket URL: `wss://www.your-ai-server.com/ws`

### 7.3 실제 플로우 테스트
1. MCP 앱 실행 (로컬 EXE 또는 `python main.py`)
2. PTT로 음성 입력 (예: “쿠팡에서 우유 검색해줘”)
3. tool_calls 수신 확인 (콘솔 로그 또는 UI 상태)
4. 브라우저 자동화 실행 확인 (검색 결과 페이지 이동)
5. OCR/HTML 결과가 서버로 전송되는지 확인
6. TTS 응답이 로컬에서 재생되는지 확인

---

## 9. 운영 체크리스트

- [ ] Docker 컨테이너 `herewego-ai` 정상 기동
- [ ] GPU 사용 가능 여부 확인 (`/usr/lib/wsl/lib/nvidia-smi -L`)
- [ ] `wss://www.your-ai-server.com/ws` 연결 가능
- [ ] TTS 음성 정상 수신/재생

---

## 10. 문제 발생 시 (빠른 트러블슈팅)

### 9.1 Docker 빌드 실패 (DNS)
- Docker Hub 연결 실패 시 `resolv.conf` DNS 확인

### 9.2 ASR 모델 로딩 실패
- 캐시 볼륨 삭제 후 재다운로드

### 9.3 HTTPS 502/405
- Nginx proxy_pass가 127.0.0.1:8000으로 연결되는지 확인
- 405는 HEAD 요청일 수 있으므로 GET으로 확인

### 9.4 WebSocket 404
- Nginx에 `/ws` 업그레이드 설정 필요
- `location /ws`에 `Upgrade`/`Connection` 헤더 추가

### 9.5 ASR 모델 다운로드 오류 (Xet/CAS)
- `HF_HUB_DISABLE_XET=1` 설정 후 재시작

### 9.6 Docker 빌드 캐시 오류
- `docker builder prune -f` 후 재빌드

### 9.7 `websocket` 응답이 localhost로 나오는 경우
- `PUBLIC_BASE_URL` 또는 `PUBLIC_WS_URL` 환경변수 설정

---

## 11. WebSocket 메시지 요약

> 상세 스키마는 `docs/WEBSOCKET_PROTOCOL.md`를 따름

### 9.1 A → B (클라이언트 → 서버)

- `audio_chunk`: PTT 음성 청크 (base64, is_final 포함)
- `command`: 텍스트 직접 명령 (ASR 우회)
- `mcp_result`: MCP 실행 결과 (OCR/HTML 포함)

### 9.2 B → A (서버 → 클라이언트)

- `asr_result`: ASR 변환 결과
- `tool_calls`: MCP 조작 명령
- `tts_chunk`: TTS 오디오 청크 스트리밍
- `error`: 에러 정보

---

## 12. 운영용 Compose 권장안 (no-reload)

운영 배포에서는 `--reload`를 제거한 별도 파일을 권장합니다.

```yaml
services:
  ai-server:
    command: ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 13. 보안/키 관리 정책

- Google 서비스 계정 JSON은 **B 서버에만 존재**
- `.env`는 서버에만 배포 (로컬 A에는 키 저장 금지)
- 로컬 A는 **TTS 재생 전용**이며, TTS 생성은 B에서만 수행

---

## 14. 향후 개선 방향

- 브랜치별 HF 캐시 분리
- 운영용 compose 파일 분리 (no-reload)
- WebSocket 메시지 스키마 문서화 강화
