# HEARBE 외부 서비스 정보

- 프로젝트: HEARBE (시각장애인 음성 쇼핑 지원)
- 작성일: 2026-02-09

## 1. 유료 외부 서비스

### 1-1. OpenAI API

| 항목 | 내용 |
|---|---|
| 용도 | AI 서버 LLM Planner (자연어 명령 → 쇼핑 액션 변환), NLU 의도 분류 |
| 사용 모델 | GPT-5 mini (`gpt-5-mini`) |
| 과금 | Input $0.25/1M tokens, Cached $0.025/1M, Output $2.00/1M tokens |
| 발급 콘솔 | https://platform.openai.com |
| 발급 방법 | 회원가입 → API Keys → Create new secret key |
| 환경변수 | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL_NAME` |
| 적용 위치 | AI 서버 (`AI/.env`) |
| 참조 파일 | `AI/core/config.py`, `AI/.env.example` |

### 1-2. Google Cloud TTS (Text-to-Speech)

| 항목 | 내용 |
|---|---|
| 용도 | AI 서버 음성 합성 (한국어 TTS) |
| 사용 모델 | Chirp 3: HD (`ko-KR-Chirp3-HD-Leda`) |
| 과금 | 무료 ~100만자/월, 이후 $30/100만자 (US$0.00003/자) |
| 발급 콘솔 | https://console.cloud.google.com |
| 발급 방법 | 1. GCP 프로젝트 생성 → 2. Cloud Text-to-Speech API 활성화 → 3. IAM → 서비스 계정 생성 → 4. JSON 키 다운로드 |
| 키 파일 배치 | `AI/config/google-service-account.json` |
| 환경변수 | `GOOGLE_APPLICATION_CREDENTIALS=config/google-service-account.json`, `TTS_GOOGLE_VOICE` |
| 적용 위치 | AI 서버 (`AI/.env`) |
| 참조 파일 | `AI/services/tts/service.py`, `AI/.env.example` |

## 2. 무료 외부 서비스

### 2-1. EmailJS

| 항목 | 내용 |
|---|---|
| 용도 | Frontend 회원가입 시 이메일 인증코드 발송 |
| 과금 | 무료 플랜 (월 200건) |
| 발급 콘솔 | https://www.emailjs.com |
| 발급 방법 | 1. 회원가입 → 2. Email Services에서 Gmail 연동 → 3. Email Templates에서 인증코드 템플릿 생성 → 4. Account → API Keys에서 Public Key 확인 |
| 환경변수 | `VITE_EMAILJS_SERVICE_ID`, `VITE_EMAILJS_TEMPLATE_ID`, `VITE_EMAILJS_PUBLIC_KEY` |
| 적용 위치 | Frontend (`Frontend/hearbe/.env`) |
| 참조 파일 | `Frontend/hearbe/src/services/emailService.js`, `Frontend/hearbe/.env.example` |

### 2-2. PeerJS + Google STUN

| 항목 | 내용 |
|---|---|
| 용도 | 보호자(S모드) 화면 공유 (WebRTC P2P 연결) |
| 과금 | 무료 (자체 호스팅 PeerJS 서버 + Google 공개 STUN) |
| PeerJS 서버 | Docker 컨테이너 `peerjs/peerjs-server` (포트 9000, 경로 `/hearbe-peer`) |
| STUN 서버 | `stun:stun.l.google.com:19302` (Google 무료 제공) |
| 환경변수 | `VITE_PEER_HOST`, `VITE_PEER_PORT`, `VITE_PEER_SECURE` |
| 적용 위치 | Frontend (`Frontend/hearbe/.env.production`) |
| 참조 파일 | `Frontend/hearbe/src/hooks/peerjs/usePeerShare.js`, `Backend/docker-compose.yml` |

## 3. 자체 호스팅 서비스 (외부 API 호출 없음)

### 3-1. Qwen3-ASR (ASR)

| 항목 | 내용 |
|---|---|
| 용도 | 음성 → 텍스트 변환 (한국어 음성 인식) |
| 모델 | `Qwen/Qwen3-ASR-0.6B` (또는 `large-v3-turbo` 선택 가능) |
| 실행 위치 | AI 서버 GPU 로컬 (Docker 컨테이너 내부) |
| 요구사항 | NVIDIA GPU + CUDA 12.x, VRAM 4GB 이상 |
| 환경변수 | `ASR_PROVIDER`, `ASR_DEVICE`, `ASR_MODEL_NAME`, `ASR_COMPUTE_TYPE` |

### 3-2. PaddleOCR

| 항목 | 내용 |
|---|---|
| 용도 | 복지카드 이미지에서 텍스트 추출 (회원가입 자동 입력), 쇼핑몰의 상풍 설명 이미지에서 텍스트 추출 |
| 실행 위치 | AI 서버 GPU 로컬 (Docker 컨테이너 내부) |
| 요구사항 | NVIDIA GPU 권장 (CPU 가능하나 느림) |
| 환경변수 | `OCR_PROVIDER=paddleocr`, `OCR_DEVICE`, `OCR_LANGUAGE=korean` |

## 4. 서비스별 환경변수 요약

| 서비스 | 환경변수 파일 | 필수 키 |
|---|---|---|
| OpenAI API | `AI/.env` | `OPENAI_API_KEY` |
| Google Cloud TTS | `AI/.env` + `AI/config/google-service-account.json` | `GOOGLE_APPLICATION_CREDENTIALS` |
| EmailJS | `Frontend/hearbe/.env` | `VITE_EMAILJS_SERVICE_ID`, `VITE_EMAILJS_TEMPLATE_ID`, `VITE_EMAILJS_PUBLIC_KEY` |
| PeerJS | `Frontend/hearbe/.env.production` | `VITE_PEER_HOST`, `VITE_PEER_PORT`, `VITE_PEER_SECURE` |
