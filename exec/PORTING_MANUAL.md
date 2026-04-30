# HEARBE 포팅 매뉴얼

- 프로젝트: HEARBE (시각장애인 음성 쇼핑 지원)
- 작성일: 2026-02-09
- 제출 경로: `exec/PORTING_MANUAL.md`
- 기준 리포지토리: `S14P11D108`

## 1. 프로젝트 구성

- Backend: `Backend` (Spring Boot API, MariaDB/Redis 연동)
- Frontend: `Frontend/hearbe` (React + Vite)
- AI: `AI` (FastAPI + ASR/NLU/LLM/TTS/OCR)

### 1-1. 운영 환경 분리 기준

- 메인 웹서버(Nginx, AWS): Backend API + Frontend 정적 파일 서빙 + PeerJS 프록시
- AI 서버: 별도 서버(Windows 노트북 + WSL2)에서 독립 운영
- Frontend에서 AI 기능(OCR, WebSocket)은 AI 서버 도메인(`your-ai-server.com`)으로 직접 호출
- 메인 웹서버 Nginx에는 AI 관련 프록시 설정 없음

## 2. 빌드/런타임 버전

### 2-1. 개발 IDE

- IntelliJ IDEA: 2025.3.1.1 (Backend 개발)
- Visual Studio Code: 1.108.1 (Frontend, AI, 인프라)

### 2-2. 메인 웹서버 (AWS, 기존 유지)

- OS: Ubuntu 24.04.3 LTS
- Kernel: 6.14.0-1018-aws
- Java: OpenJDK 17.0.18
- Node.js: v24.13.0
- npm: 11.6.2
- Docker: 29.2.0
- Docker Compose: v5.0.2
- Nginx: 1.24.0

### 2-3. AI 서버 (별도 서버, WSL2 기준 확인값)

- OS: Ubuntu 22.04.5 LTS (WSL2)
- Kernel: 6.6.87.2-microsoft-standard-WSL2
- Python: 3.10.12
- Docker: 29.1.3
- Docker Compose: v5.0.1
- GPU: NVIDIA Driver 560.94 / CUDA 12.6 (`/usr/lib/wsl/lib/nvidia-smi` 기준)

### 2-4. Backend 기준 버전 파일

- Java Toolchain: 17 (`Backend/build.gradle`)
- Spring Boot: 3.5.9 (`Backend/build.gradle`)
- WAS: Apache Tomcat 10.1.50 (Spring Boot 내장, Jakarta Servlet 6.0)
- Dependency Management Plugin: 1.1.7 (`Backend/build.gradle`)
- Gradle Wrapper: 8.14.3 (`Backend/gradle/wrapper/gradle-wrapper.properties`)
- Docker Build Image: `gradle:8-jdk17` (`Backend/Dockerfile`)
- Docker Runtime Image: `eclipse-temurin:17-jre` (`Backend/Dockerfile`)

### 2-5. Frontend 기준 버전 파일

- React: 19.2.4 (`Frontend/hearbe/package.json`)
- Vite: 7.2.4 (`Frontend/hearbe/package.json`)
- React Router DOM: 6.28.0 (`Frontend/hearbe/package.json`)
- PeerJS: 1.5.5 (`Frontend/hearbe/package.json`)

### 2-6. AI 기준 버전 파일

- Base Image: `nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04` (`AI/Dockerfile`)
- Python: 3.10 (컨테이너 설치) (`AI/Dockerfile`)
- 주요 패키지: FastAPI, Uvicorn, OpenAI SDK, Google TTS, PaddleOCR (`AI/requirements.txt`)
- GPU 예약 설정: `deploy.resources.reservations.devices` (`AI/docker-compose.yml`)

## 3. 배포 포트 및 서비스

### 3-1. Backend Compose (`Backend/docker-compose.yml`)

- Backend API: `${COMPOSE_HOST_PORT}:8080` (기본값: `8080`)
- MariaDB: `3306:3306`
- Redis: `6379:6379`
- phpMyAdmin: `8108:80`
- PeerJS: `9000:9000` (경로: `/hearbe-peer`)

### 3-2. AI Compose (`AI/docker-compose.yml`)

- AI API: `8000:8000`
- 내부 실행 명령: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

### 3-3. Reverse Proxy (메인 웹서버 Nginx 실제 설정)

설정 파일: `/etc/nginx/sites-available/default`

- HTTPS: `443` (Let's Encrypt, `i14d108.p.ssafy.io`)
- HTTP → HTTPS 리다이렉트 (Certbot 자동 설정)
- Frontend 정적 파일: `location /` → `Frontend/hearbe/dist` (try_files, SPA 폴백)
- Backend API 프록시: `location /api/` → `http://127.0.0.1:8080/` (rate-limit 적용: `limit_req zone=api_rl burst=20 nodelay`)
- PeerJS WebSocket 프록시: `location /hearbe-peer/` → `http://127.0.0.1:9000` (Upgrade/Connection 헤더 포함)
- 보안 헤더: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`
- 숨김파일 차단: `location ~* /\.(?!well-known)` → deny all

참고: AI 서버는 별도 도메인(`your-ai-server.com`)으로 운영되며, 메인 웹서버 Nginx에 AI 관련 프록시 설정은 없음. Frontend에서 AI API를 직접 호출하는 구조.

## 4. Git Clone 이후 빌드/배포 절차

### 4-0. 선행 조건 (웹서버)

```bash
# 아래 도구가 설치되어 있어야 함
docker --version          # 29.x 이상
docker compose version    # v5.x 이상
node --version            # v24.x 이상
npm --version             # 11.x 이상
nginx -v                  # 1.24.x 이상
```

### 4-1. Backend

```bash
cd Backend
cp .env.example .env
```

`.env` 필수 변경 항목 (나머지는 기본값 사용 가능):

| 변수 | 설명 | 예시 |
|---|---|---|
| `SPRING_DATASOURCE_PASSWORD` | DB 비밀번호 | 임의 지정 |
| `SPRING_DATA_REDIS_PASSWORD` | Redis 비밀번호 | 임의 지정 |
| `JWT_SECRET` | JWT 서명 키 (256-bit 이상) | `openssl rand -base64 32` 로 생성 |
| `ENCRYPTION_SECRET_KEY` | 암호화 키 (32 bytes) | `openssl rand -base64 32` 로 생성 |
| `MYSQL_ROOT_PASSWORD` | MariaDB root 비밀번호 | 임의 지정 |
| `MYSQL_PASSWORD` | MariaDB 앱 계정 비밀번호 | `SPRING_DATASOURCE_PASSWORD`와 동일하게 |
| `PMA_PASSWORD` | phpMyAdmin 비밀번호 | `MYSQL_PASSWORD`와 동일하게 |
| `REDIS_PASSWORD` | Redis 비밀번호 | `SPRING_DATA_REDIS_PASSWORD`와 동일하게 |
| `COMPOSE_HOST_PORT` | Backend 외부 포트 | `8080` (기본값) |

```bash
docker compose build
docker compose up -d

docker compose ps
docker compose logs --tail=200 hearbe-backend
```

검증:

```bash
curl -i http://localhost:8080/health
curl -i http://localhost:8080/ping
```

### 4-2. Frontend

```bash
cd Frontend/hearbe
cp .env.example .env
```

환경 파일 구조 (Vite 빌드 동작):

| 파일 | 용도 | 로딩 시점 |
|---|---|---|
| `.env` | 공통 변수 (EmailJS 등) | `npm run dev` + `npm run build` 모두 |
| `.env.production` | 배포용 변수 (API URL, PeerJS 등) | `npm run build` 시에만 `.env`를 덮어씀 |

- **로컬 개발**: `.env`의 `VITE_API_BASE_URL=http://localhost:8080` 사용
- **프로덕션 배포**: `.env.production`의 `VITE_API_BASE_URL`이 우선 적용됨
- `.env`의 EmailJS 키는 프로덕션 빌드에서도 함께 로딩됨 (Vite 기본 동작)

프로덕션 배포 시 `.env.production` 확인 항목:

| 변수 | 현재 값 | 비고 |
|---|---|---|
| `VITE_API_BASE_URL` | `https://i14d108.p.ssafy.io/api` | 도메인 변경 시 수정 |
| `VITE_API_URL` | `https://i14d108.p.ssafy.io/api` | PeerJS 설정에서 참조 |
| `VITE_PEER_HOST` | `i14d108.p.ssafy.io` | 도메인 변경 시 수정 |
| `VITE_PEER_PORT` | `443` | HTTPS 기본 |
| `VITE_PEER_SECURE` | `true` | HTTPS 사용 시 true |
| `VITE_OCR_WELFARE_CARD_URL` | `https://your-ai-server.com/api/v1/ocr/welfare-card` | AI 서버 도메인 |

```bash
npm install
npm run build
# 빌드 결과물: dist/ → Nginx가 직접 서빙
```

### 4-3. AI 서버 (별도 서버/별도 환경) — 처음부터 따라하기

> AI 서버는 **메인 웹서버(AWS)와 완전히 분리된 별도 서버**에서 실행됩니다.
> GPU가 필요하며, 현재 프로젝트는 Windows 노트북 + WSL2 환경에서 운영 중입니다.

#### STEP 0. 사전 요구사항 확인

AI 서버를 구동하려면 아래 환경이 **반드시** 갖춰져 있어야 합니다.

| 항목 | 최소 요구 | 확인 명령어 |
|---|---|---|
| OS | Ubuntu 22.04+ (또는 WSL2) | `cat /etc/os-release` |
| Python | 3.10+ | `python3 --version` |
| Docker | 29.x+ | `docker --version` |
| Docker Compose | v5.x+ | `docker compose version` |
| NVIDIA Driver | 560+ | 아래 GPU 확인 참고 |
| CUDA | 12.x+ | Docker 컨테이너 내부에서 확인 |
| NVIDIA Container Toolkit | 설치 필수 | `docker run --rm --gpus all nvidia/cuda:12.3.2-base-ubuntu22.04 nvidia-smi` |

**GPU 확인 방법** (WSL2 환경에서는 호스트 `nvidia-smi`가 segfault 발생할 수 있으므로 Docker로 확인):

```bash
# 방법 1: Docker로 GPU 확인 (가장 확실)
docker run --rm --gpus all nvidia/cuda:12.3.2-base-ubuntu22.04 nvidia-smi

# 방법 2: 호스트에서 직접 확인 (WSL2에서 segfault 발생 가능)
nvidia-smi
# 또는
/usr/lib/wsl/lib/nvidia-smi
```

> **NVIDIA Container Toolkit 미설치 시?** Docker가 GPU를 인식하지 못합니다.
> 설치 가이드: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

#### STEP 1. 소스코드 클론 및 AI 디렉토리 이동

```bash
git clone <리포지토리 URL>
cd S14P11D108/AI
```

#### STEP 2. 환경 변수 파일 생성

```bash
cp .env.example .env
```

`.env` 파일을 열어 **반드시 수정해야 하는 값**을 입력합니다:

| 변수 | 필수 여부 | 설명 | 예시 |
|---|---|---|---|
| `OPENAI_API_KEY` | **필수** | OpenAI API 키 (LLM Planner에 사용) | `sk-proj-xxxxx...` |
| `GMS_API_KEY` | 선택 | 대체 LLM API 키 (미사용 시 빈값) | `sp-xxxxx...` |
| `CORS_ORIGINS` | **필수** | Frontend 도메인 (쉼표 구분) | `https://i14d108.p.ssafy.io,http://localhost:5173` |
| `APP_ENV` | 권장 | 환경 모드 (`dev` 또는 `prod`) | `dev` |

> 나머지 변수는 기본값으로 동작합니다. 상세한 변수 설명은 **섹션 6-3**을 참고하세요.

#### STEP 3. Google Cloud TTS 서비스 계정 파일 배치

TTS(음성 합성) 기능 사용을 위해 Google Cloud 서비스 계정 JSON 파일이 필요합니다.

```bash
# config 디렉토리 확인 (이미 존재해야 함)
ls config/

# 서비스 계정 JSON 파일을 아래 경로에 배치
# 파일명: config/google-service-account.json
```

> **서비스 계정 JSON 발급 방법:**
> 1. https://console.cloud.google.com 접속
> 2. 프로젝트 선택 → "IAM 및 관리자" → "서비스 계정"
> 3. 서비스 계정 생성 → "Cloud Text-to-Speech API" 권한 부여
> 4. 키 생성 (JSON) → 다운로드한 파일을 `config/google-service-account.json`에 저장

#### STEP 4. Docker 이미지 빌드

```bash
docker compose build
```

> **빌드에 10~20분 소요**됩니다 (CUDA, PaddlePaddle, PyTorch 등 대용량 패키지 설치).
> 빌드 중 에러가 나면 인터넷 연결과 Docker 디스크 여유 공간(최소 20GB)을 확인하세요.

#### STEP 5. 컨테이너 실행

```bash
docker compose up -d
```

#### STEP 6. 실행 상태 확인

```bash
# 컨테이너 상태 확인 (STATUS가 healthy 또는 Up이면 정상)
docker compose ps

# 로그 확인 (모델 로딩 완료까지 1~2분 대기)
docker compose logs --tail=200 ai-server

# GPU가 컨테이너에서 정상 인식되는지 확인
docker compose exec ai-server nvidia-smi
```

> **주의:** 컨테이너 시작 후 ASR/OCR 모델 로딩에 약 1~2분이 소요됩니다.
> `docker compose logs -f ai-server`로 로그를 실시간 확인하며 `Application startup complete` 메시지를 기다리세요.

#### STEP 7. 동작 검증

```bash
# 기본 헬스체크 (200 OK 반환되면 정상)
curl -i http://localhost:8000/

# 상세 헬스체크
curl -i http://localhost:8000/api/v1/health

# ASR 서비스 상태 확인
curl -i http://localhost:8000/api/v1/health/asr
```

> `/api/v1/health/tts`는 현재 설정 필드 참조 불일치로 500을 반환할 수 있으나,
> 실제 TTS 기능(WebSocket을 통한 음성 합성)은 정상 동작합니다. (섹션 11-1 참고)

#### 빠른 배포 (이미 빌드된 환경에서 코드 업데이트 시)

```bash
cd AI
# 배포 스크립트 사용 (빌드 + 재시작을 한 번에 수행)
bash deployDockerCompose.sh
```

> `deployDockerCompose.sh`는 `날짜-git해시` 형태의 태그를 자동 생성하고 `docker compose up -d --build`를 실행합니다.

#### 컨테이너 중지/재시작

```bash
# 중지
docker compose down

# 재시작 (이미지 재빌드 없이)
docker compose up -d

# 재시작 (이미지 재빌드 포함)
docker compose up -d --build
```

## 5. 기능 목록 (요약)

### 5-1. Frontend

- 인증/회원: 로그인, 회원가입, 아이디 찾기, 비밀번호 재설정
- 모드 분기: A/B/C/S 라우팅 및 사용자 타입별 화면
- 쇼핑 기능: 몰 선택, 장바구니, 위시리스트, 주문내역
- 보호자 공유: 공유코드 + PeerJS 기반 화면 공유
- 복지카드 OCR 연동(회원가입 자동입력)
- 이메일 인증(EmailJS)

근거 파일:
- `Frontend/hearbe/src/router/AppRouter.jsx`
- `Frontend/hearbe/src/services/authAPI.js`
- `Frontend/hearbe/src/hooks/peerjs/usePeerShare.js`
- `Frontend/hearbe/src/services/emailService.js`

### 5-2. Backend

- 인증: 회원가입/로그인/토큰재발급/회원탈퇴/아이디찾기/비밀번호재설정
- 회원: 프로필 조회/수정, 복지카드 CRUD
- 장바구니: 생성/조회/수정/삭제
- 위시리스트: 생성/조회/삭제
- 주문: 주문 생성/내 주문 조회
- 공유: 공유코드 발급/조회
- 공통: JWT 인증 필터, 헬스체크, 예외 처리

근거 파일:
- `Backend/src/main/java/com/ssafy/d108/backend/auth/controller/AuthController.java`
- `Backend/src/main/java/com/ssafy/d108/backend/member/controller/ProfileController.java`
- `Backend/src/main/java/com/ssafy/d108/backend/member/controller/WelfareCardController.java`
- `Backend/src/main/java/com/ssafy/d108/backend/cartItem/controller/CartItemController.java`
- `Backend/src/main/java/com/ssafy/d108/backend/wishlist/controller/WishlistController.java`
- `Backend/src/main/java/com/ssafy/d108/backend/order/controller/OrderController.java`
- `Backend/src/main/java/com/ssafy/d108/backend/global/controller/ShareCodeController.java`

### 5-3. AI

- ASR: Whisper / Qwen3-ASR
- NLU: 의도/컨텍스트 처리
- LLM Planner: 자연어 명령 계획
- TTS: Google Cloud TTS
- OCR: PaddleOCR 기반 복지카드 인식
- 통신: FastAPI HTTP + WebSocket `/ws`

근거 파일:
- `AI/main.py`
- `AI/api/http.py`
- `AI/core/config.py`
- `AI/services/tts/service.py`
- `AI/services/summarizer/ocr_integrator.py`

## 6. 환경 변수 정리 (코드/설정 파일 기준)

주의:
- 민감정보(API Key/비밀번호/시크릿)는 Git에 직접 커밋하지 않음
- 실제 값은 배포 서버 시크릿 또는 `.env`에만 주입

### 6-1. Backend 변수 (`Backend/.env.example` 기준)

템플릿: `Backend/.env.example` → `Backend/.env`로 복사 후 값 수정

- App/DB/Redis/JPA
  - `SPRING_APPLICATION_NAME` — 앱 이름 (기본값: `hearbe-backend`)
  - `SPRING_DATASOURCE_URL` — MariaDB JDBC URL (Docker 내부 호스트명 사용)
  - `SPRING_DATASOURCE_USERNAME` — DB 계정 (기본값: `hearbe`)
  - `SPRING_DATASOURCE_PASSWORD` — DB 비밀번호 (**반드시 변경**)
  - `SPRING_DATA_REDIS_HOST` — Redis 호스트 (기본값: `hearbe-redis`)
  - `SPRING_DATA_REDIS_PORT` — Redis 포트 (기본값: `6379`)
  - `SPRING_DATA_REDIS_PASSWORD` — Redis 비밀번호 (**반드시 변경**)
  - `SPRING_JPA_HIBERNATE_DDL_AUTO` — DDL 전략 (기본값: `update`)

- Auth/암호화
  - `JWT_SECRET` — JWT 서명 키, 256-bit 이상 (**반드시 변경**)
  - `JWT_EXPIRATION` — 토큰 만료 시간(ms) (기본값: `3600000`)
  - `ENCRYPTION_SECRET_KEY` — 암호화 키, 32 bytes (**반드시 변경**)

- Docker Compose 실행 제어
  - `COMPOSE_HOST_PORT` — Backend 외부 바인딩 포트 (기본값: `8080`)
  - `COMPOSE_HOST_LOG_PATH` — 로그 마운트 경로 (기본값: `./logs`)
  - `COMPOSE_APP_PROFILE` — Spring 프로파일 (기본값: `dev`)

- 인프라 컨테이너
  - `MYSQL_ROOT_PASSWORD` — MariaDB root 비밀번호 (**반드시 변경**)
  - `MYSQL_DATABASE` — DB명 (기본값: `hearbe`)
  - `MYSQL_USER` — DB 계정 (기본값: `hearbe`)
  - `MYSQL_PASSWORD` — DB 비밀번호 (`SPRING_DATASOURCE_PASSWORD`와 동일)
  - `PMA_HOST` — phpMyAdmin 대상 호스트 (기본값: `hearbe-mariadb`)
  - `PMA_USER` / `PMA_PASSWORD` — phpMyAdmin 접속 계정
  - `REDIS_PASSWORD` — Redis 비밀번호 (`SPRING_DATA_REDIS_PASSWORD`와 동일)

- 로깅
  - `LOG_LEVEL`, `APP_LOG_LEVEL`, `SPRING_LOG_LEVEL`, `SPRING_SECURITY_LOG_LEVEL`, `SPRING_DATA_LOG_LEVEL`
  - `HIBERNATE_SQL_LOG_LEVEL`, `HIBERNATE_BINDER_LOG_LEVEL`, `SPRING_JPA_SHOW_SQL`

### 6-2. Frontend 변수

템플릿: `Frontend/hearbe/.env.example` → `Frontend/hearbe/.env`로 복사 후 값 수정

`.env` (공통, 개발+빌드 모두 로딩):

- `VITE_API_BASE_URL` — Backend API URL (로컬: `http://localhost:8080`)
- `VITE_OCR_WELFARE_CARD_URL` — AI OCR 엔드포인트
- `VITE_EMAILJS_SERVICE_ID` — EmailJS 서비스 ID
- `VITE_EMAILJS_TEMPLATE_ID` — EmailJS 템플릿 ID
- `VITE_EMAILJS_PUBLIC_KEY` — EmailJS 공개 키

`.env.production` (프로덕션 빌드 전용, `.env` 값을 덮어씀):

- `VITE_API_BASE_URL` — 배포 도메인 API URL
- `VITE_API_URL` — PeerJS 설정에서 참조하는 API URL
- `VITE_PEER_HOST` — PeerJS 서버 호스트 (배포 도메인)
- `VITE_PEER_PORT` — PeerJS 서버 포트 (`443`)
- `VITE_PEER_SECURE` — HTTPS 사용 여부 (`true`)
- `VITE_OCR_WELFARE_CARD_URL` — AI OCR 엔드포인트 (배포용)

코드 참조만 존재 (기본값 폴백):
- `VITE_SOCKET_SERVER_URL` — AI WebSocket URL (미설정 시 `http://localhost:4000`)

### 6-3. AI 변수 (`AI/.env.example` 기준)

템플릿: `AI/.env.example` → `AI/.env`로 복사 후 값 수정

> **필수 표시(★)가 있는 변수는 반드시 실제 값을 입력**해야 합니다.
> 나머지는 기본값으로 동작하므로 초기 구동 시 변경하지 않아도 됩니다.

#### 서버/접속 설정

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `APP_ENV` | | `dev` | 환경 모드. `dev`(개발) 또는 `prod`(운영). 로그 레벨 등이 자동으로 변경됨 |
| `SERVER_HOST` | | `0.0.0.0` | 서버 바인딩 주소. Docker에서는 `0.0.0.0` 그대로 사용 |
| `SERVER_PORT` | | `8000` | 서버 포트 |
| `DEBUG` | | `false` | 디버그 모드 활성화 여부 |
| `CORS_ORIGINS` | ★ | `http://localhost:3000,http://localhost:5173` | **CORS 허용 도메인** (쉼표 구분). Frontend 배포 도메인을 반드시 추가 |
| `PUBLIC_BASE_URL` | | (미설정) | 클라이언트가 접근하는 외부 URL (예: `https://your-ai-server.com`) |
| `PUBLIC_WS_URL` | | (미설정) | WebSocket 외부 URL (예: `wss://your-ai-server.com/ws`) |
| `MAIN_PAGE_URL` | | (미설정) | 메인 페이지 URL |
| `BACKEND_BASE_URL` | | (미설정) | Backend API 베이스 URL |
| `BACKEND_URL` | | (미설정) | Backend 연동 URL |
| `GENERAL_URL` | | (미설정) | 일반 사용자 URL |
| `BLIND_URL` | | (미설정) | 시각장애인용 URL |
| `LOW_VISION_URL` | | (미설정) | 저시력 사용자용 URL |

#### ASR (음성 인식) 설정

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `ASR_PROVIDER` | | `whisper` | ASR 엔진 선택. `whisper`(Faster-Whisper) 또는 `qwen3`(Qwen3-ASR) |
| `ASR_DEVICE` | | `cuda` | 연산 장치. `cuda`(GPU) 또는 `cpu` |
| `ASR_LANGUAGE` | | `ko` | 인식 언어 (한국어: `ko`) |
| `ASR_MODEL_NAME` | | `turbo` | Whisper 모델명. `tiny`/`base`/`small`/`medium`/`large-v3`/`turbo` 중 선택. `turbo` 권장 |
| `ASR_COMPUTE_TYPE` | | `float16` | Whisper 연산 타입. `float16`(기본)/`float32`/`int8`(VRAM 부족 시) |
| `ASR_BEAM_SIZE` | | `5` | Whisper 빔서치 크기 (높을수록 정확하나 느림) |
| `ASR_QWEN3_MODEL_NAME` | | `Qwen/Qwen3-ASR-0.6B` | Qwen3 모델 (0.6B: 2GB VRAM, 1.7B: 5GB VRAM) |
| `ASR_QWEN3_MAX_BATCH_SIZE` | | `32` | Qwen3 최대 배치 크기 |
| `ASR_QWEN3_MAX_NEW_TOKENS` | | `256` | Qwen3 최대 생성 토큰 수 |

#### NLU (자연어 이해) 설정

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `NLU_INTENT_MODEL` | | (코드 기본값) | 의도 분류 모델명 |
| `NLU_NER_ENABLED` | | (코드 기본값) | 개체명 인식 활성화 여부 |
| `NLU_CONTEXT_WINDOW` | | (코드 기본값) | 대화 컨텍스트 윈도우 크기 |

#### LLM (대규모 언어 모델) 설정

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `OPENAI_API_KEY` | ★ | (없음) | **OpenAI API 키**. https://platform.openai.com 에서 발급 |
| `OPENAI_BASE_URL` | | `https://api.openai.com/v1` | OpenAI API 엔드포인트 URL |
| `GMS_API_KEY` | | (없음) | 대체 LLM API 키 (미사용 시 빈값) |
| `LLM_API_KEY_NAME` | | `OPENAI_API_KEY` | 사용할 API 키 변수명 선택 |
| `LLM_MODEL_NAME` | | `gpt-5-mini` | LLM 모델명 |
| `LLM_MAX_TOKENS` | | `8192` | 최대 응답 토큰 수 |
| `LLM_COMMAND_MAX_TOKENS` | | (코드 기본값) | 명령 처리 최대 토큰 |
| `LLM_TTS_MAX_TOKENS` | | (코드 기본값) | TTS용 텍스트 최대 토큰 |
| `LLM_TEMPERATURE` | | `0.7` | 응답 다양성 (0.0~1.0, 낮을수록 일관적) |
| `LLM_TIMEOUT` | | `30` | API 호출 타임아웃 (초) |
| `LLM_DEBUG_LOG` | | `false` | LLM 디버그 로그 출력 여부 |

#### TTS (음성 합성) 설정 — Google Cloud TTS

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | ★ | `config/google-service-account.json` | **Google 서비스 계정 JSON 파일 경로**. 이 파일이 없으면 TTS 기능 불가 |
| `TTS_GOOGLE_VOICE` | | `ko-KR-Chirp3-HD-Leda` | 음성 선택 (Leda: 여성, Puck: 남성 등) |
| `TTS_SAMPLE_RATE` | | `24000` | 오디오 샘플레이트 (Hz) |
| `TTS_STREAMING` | | `true` | 스트리밍 TTS 활성화 |
| `TTS_SPEAKING_RATE` | | (코드 기본값) | 말하기 속도 |

#### OCR (문자 인식) 설정 — PaddleOCR

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `OCR_PROVIDER` | | `paddleocr` | OCR 엔진 (`paddleocr`/`openai`/`tesseract`) |
| `OCR_LANGUAGE` | | `korean` | 인식 언어 |
| `OCR_DEVICE` | | `gpu` | 연산 장치 (`gpu` 또는 `cpu`) |
| `OCR_API_KEY` | | (없음) | 외부 OCR API 키 (PaddleOCR 사용 시 불필요) |
| `OCR_HTTP_MAX_UPLOAD_MB` | | `20` | 이미지 업로드 최대 크기 (MB) |
| `OCR_HTTP_TIMEOUT_SECONDS` | | `45` | OCR 처리 타임아웃 (초) |

#### Flow Engine 설정

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `FLOWS_DIR` | | `flows` | Flow 정의 파일 디렉토리 |
| `DEFAULT_SITE` | | `coupang` | 기본 쇼핑몰 사이트 |
| `FLOW_CONFIRMATION_REQUIRED` | | `true` | 액션 실행 전 확인 요청 여부 |
| `SEARCH_MATCH_THRESHOLD` | | (코드 기본값) | 검색 매칭 임계값 |
| `SEARCH_MATCH_USE_LLM` | | (코드 기본값) | LLM 기반 매칭 사용 여부 |
| `SEARCH_MATCH_LLM_MODEL` | | (코드 기본값) | 매칭에 사용할 LLM 모델 |

#### 로깅 설정

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `LOG_LEVEL` | | `INFO` | 전체 로그 레벨 (`DEBUG`/`INFO`/`WARNING`/`ERROR`) |
| `LOG_CONSOLE_LEVEL` | | (APP_ENV에 따라 자동) | 콘솔 출력 로그 레벨 |
| `LOG_FILE_LEVEL` | | (APP_ENV에 따라 자동) | 파일 저장 로그 레벨 |
| `LOG_DIR` | | `logs` | 로그 저장 디렉토리 |
| `LOG_FILE` | | `ai_server.log` | 로그 파일명 |
| `LOG_ROTATE_WHEN` | | `midnight` | 로그 로테이션 주기 |
| `LOG_ROTATE_INTERVAL` | | `1` | 로테이션 간격 |
| `LOG_BACKUP_COUNT` | | `7` (dev) / `30` (prod) | 보관할 로그 파일 수 |
| `LOG_ROTATE_UTC` | | `true` | UTC 기준 로테이션 여부 |

> **프로파일 오버라이드:** `APP_ENV=dev`이면 `DEV_*` 접두사 변수가, `APP_ENV=prod`이면 `PROD_*` 접두사 변수가 위 로깅 설정을 자동으로 덮어씁니다. (예: `DEV_LOG_LEVEL=DEBUG`, `PROD_LOG_LEVEL=INFO`)

#### Docker Compose에서 추가 참조되는 변수

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `TAG` | | `latest` | Docker 이미지 태그. `deployDockerCompose.sh` 사용 시 자동 생성 |
| `ELEVENLABS_API_KEY` | | (없음) | ElevenLabs TTS API 키 (현재 미사용) |
| `HF_HUB_DISABLE_XET` | | `1` (compose 고정) | HuggingFace Hub XET 비활성화 (compose에서 자동 설정) |

### 6-4. 현재 `.env` 파일 존재 여부

- 웹서버 기준:
  - 존재: `Backend/.env` (키 확인 완료)
  - 존재: `Frontend/hearbe/.env` (개발용, EmailJS 키 포함)
  - 존재: `Frontend/hearbe/.env.production` (배포용, API/PeerJS/OCR URL)
- AI 별도 서버 기준:
  - `AI/.env`는 AI 별도 서버에만 존재 (웹서버에는 없음)

## 7. DB 접속 정보 및 ERD/프로퍼티 파일 목록

### 7-1. DB/계정 관련 핵심 파일

- `Backend/src/main/resources/application.properties`
- `Backend/.env.example`
- `Backend/.env` (실서버 값, 민감정보)
- `Backend/docker-compose.yml`

### 7-2. ERD/초기 데이터

- ERD 문서: `Backend/docs/erd/erd.md`
- 시드 데이터: `Backend/src/main/resources/data.sql`

### 7-3. DB 덤프 제출

- 제출 파일: `exec/db_dump_20260209.sql` (2026-02-09 기준 최신본)
- DB명: `hearbe` (MariaDB)
- 덤프 재생성 시:

```bash
docker exec hearbe-mariadb mariadb-dump \
  -u root -p"${MYSQL_ROOT_PASSWORD}" \
  --single-transaction hearbe > exec/db_dump_YYYYMMDD.sql
```

## 8. 외부 서비스 목록

### 8-1. 유료 API (AI 서버에서 사용)

| 서비스 | 용도 | 모델 | 과금 | 환경변수 |
|---|---|---|---|---|
| OpenAI API | LLM Planner / NLU 의도 분류 | GPT-5 mini | Input $0.25/1M tokens, Cached $0.025/1M, Output $2.00/1M tokens | `OPENAI_API_KEY`, `LLM_MODEL_NAME` |
| Google Cloud TTS | 음성 합성 | Chirp 3: HD | 무료 ~100만자, 이후 $30/100만자 (US$0.00003/자) | `GOOGLE_APPLICATION_CREDENTIALS`, `TTS_GOOGLE_VOICE` |

- OpenAI: https://platform.openai.com
- Google Cloud: https://console.cloud.google.com (서비스계정 JSON 발급 필요, `config/google-service-account.json`에 배치)

### 8-2. 무료 서비스

| 서비스 | 용도 | 적용 위치 | 비고 |
|---|---|---|---|
| EmailJS | Frontend 이메일 인증코드 발송 | `VITE_EMAILJS_SERVICE_ID`, `VITE_EMAILJS_TEMPLATE_ID`, `VITE_EMAILJS_PUBLIC_KEY` | https://www.emailjs.com (무료 플랜) |
| PeerJS + STUN | 보호자 화면 공유 (WebRTC) | `VITE_PEER_HOST`, `VITE_PEER_PORT`, `VITE_PEER_SECURE` | STUN: `stun:stun.l.google.com:19302` (무료) |

### 8-3. 자체 호스팅 (외부 API 호출 없음)

| 서비스 | 용도 | 모델 | 실행 위치 |
|---|---|---|---|
| ASR (음성 인식) | 음성→텍스트 변환 | Faster-Whisper large-v3-turbo / Qwen3-ASR-0.6B | AI 서버 GPU 로컬 |
| OCR (문자 인식) | 복지카드 텍스트 추출 | PaddleOCR | AI 서버 GPU 로컬 |

## 9. AI 서버 별도 환경 세팅 가이드 (처음 하는 사람용)

> 이 섹션은 **AI 서버를 처음 세팅하는 사람**을 위한 단계별 체크리스트입니다.
> 섹션 4-3의 STEP들을 모두 완료한 후, 아래 항목으로 최종 점검하세요.

### 9-1. 인프라/런타임 확인

아래 명령어를 **하나씩** 실행하여 결과를 확인합니다.

```bash
# 1. OS 확인 (Ubuntu 22.04+ 필요)
cat /etc/os-release

# 2. Python 확인 (3.10+ 필요, 없어도 Docker가 처리하므로 참고용)
python3 --version

# 3. Docker 확인 (29.x+ 필요)
docker --version

# 4. Docker Compose 확인 (v5.x+ 필요)
docker compose version
```

**GPU 확인** (가장 중요!):

```bash
# Docker로 GPU 접근 가능한지 확인 (이 명령이 성공해야 AI 서버 구동 가능)
docker run --rm --gpus all nvidia/cuda:12.3.2-base-ubuntu22.04 nvidia-smi
```

> **이 명령이 실패하면?**
> - `could not select device driver`: NVIDIA Container Toolkit 미설치 → [설치 가이드](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) 참고
> - `no matching manifest`: Docker 이미지 아키텍처 불일치 → `docker pull nvidia/cuda:12.3.2-base-ubuntu22.04` 먼저 실행
> - WSL2에서 호스트 `nvidia-smi`가 segfault 나는 것은 정상 (알려진 이슈). Docker 내부에서만 확인하면 됩니다.

2026-02-09 실환경 확인 결과:
- WSL2 호스트 `nvidia-smi` segfault 발생 (WSL2 알려진 이슈)
- 컨테이너 내부 GPU 정상 인식: NVIDIA Driver 560.94 / CUDA 12.6

### 9-2. 파일 배치 체크리스트

컨테이너를 올리기 전에 아래 파일들이 모두 준비되었는지 확인합니다.

```bash
cd AI

# 1. .env 파일 존재 확인
ls -la .env
# → 파일이 없으면: cp .env.example .env 후 값 수정

# 2. Google 서비스 계정 파일 확인
ls -la config/google-service-account.json
# → 파일이 없으면: Google Cloud Console에서 발급 후 배치 (섹션 4-3 STEP 3 참고)

# 3. Docker Compose 설정 검증 (문법 오류 확인)
docker compose config
# → 에러 없이 YAML이 출력되면 정상
```

### 9-3. 컨테이너 실행 및 상태 확인

```bash
# 1. 컨테이너 실행
docker compose up -d

# 2. 상태 확인 (STATUS가 Up 또는 healthy여야 정상)
docker compose ps

# 3. 로그 확인 (모델 로딩 완료 대기, 1~2분 소요)
docker compose logs -f ai-server
# → "Application startup complete" 메시지가 보이면 정상
# → Ctrl+C로 로그 추적 종료

# 4. GPU가 컨테이너 내부에서 인식되는지 확인
docker compose exec ai-server nvidia-smi
```

### 9-4. 헬스체크 (서비스 정상 동작 확인)

```bash
# 기본 헬스 (200 OK면 정상)
curl -i http://localhost:8000/

# 상세 헬스 (200 OK면 정상)
curl -i http://localhost:8000/api/v1/health

# ASR(음성인식) 상태 (200 OK면 정상)
curl -i http://localhost:8000/api/v1/health/asr

# TTS(음성합성) 상태 — 현재 500 반환 가능 (섹션 11-1 참고, 실제 TTS 기능은 정상)
curl -i http://localhost:8000/api/v1/health/tts
```

2026-02-09 실환경 확인 결과:
- `/` → 200 OK, `/api/v1/health` → 200 OK, `/api/v1/health/asr` → 200 OK
- `/api/v1/health/tts` → 500 (상태조회 API 필드 불일치, 실제 TTS 기능은 WebSocket으로 정상 동작)

### 9-5. 트러블슈팅 가이드

| 증상 | 원인 | 해결 방법 |
|---|---|---|
| `docker compose up` 시 GPU 관련 에러 | NVIDIA Container Toolkit 미설치 | [설치 가이드](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) 참고 |
| 컨테이너가 즉시 종료됨 | `.env` 파일 누락 또는 문법 오류 | `docker compose logs ai-server`로 에러 확인 |
| `OPENAI_API_KEY` 관련 에러 | API 키 미설정 또는 만료 | `.env`에서 `OPENAI_API_KEY` 값 확인 |
| TTS 기능 불가 | Google 서비스 계정 파일 미배치 | `config/google-service-account.json` 존재 확인 |
| OCR 처리 매우 느림 | GPU 미인식으로 CPU 폴백 | `docker compose exec ai-server nvidia-smi`로 GPU 확인 |
| 빌드 중 디스크 부족 에러 | Docker 이미지 캐시 누적 | `docker system prune -a`로 미사용 이미지 정리 |
| `CORS` 에러 (브라우저 콘솔) | `CORS_ORIGINS`에 Frontend 도메인 미등록 | `.env`의 `CORS_ORIGINS`에 도메인 추가 |
| WebSocket 연결 실패 | 방화벽 또는 Reverse Proxy 설정 | 8000 포트 개방 및 `/ws` 경로 프록시 확인 |
| 모델 다운로드 실패 | 네트워크 불안정 또는 HuggingFace 접근 차단 | 재시도 또는 프록시 설정 확인 |

### 9-6. 운영 최종 확인 체크리스트

- [ ] `AI/.env` 생성 완료 및 `OPENAI_API_KEY` 입력
- [ ] `config/google-service-account.json` 배치 완료
- [ ] `CORS_ORIGINS`에 Frontend 배포 도메인 등록
- [ ] GPU 메모리 여유 확인 (ASR + OCR 모델 로딩에 약 4~6GB VRAM 필요)
- [ ] 외부 API 키(OpenAI) 유효성 확인 (잔액/만료일)
- [ ] 헬스체크 정상 응답 (`/`, `/api/v1/health`, `/api/v1/health/asr`)
- [ ] Frontend에서 AI 서버 도메인으로 접근 가능 (방화벽/포트 확인)
- [ ] 로그 저장 경로(`AI/logs`) 쓰기 권한 확인

## 10. 배포 시 특이사항

### 10-1. 웹서버 (AWS)

- Nginx에서 Backend API(`/api/`)에 rate-limit(`limit_req zone=api_rl burst=20 nodelay`) 적용 중
- Frontend는 `npm run build` 후 `dist/` 디렉토리를 Nginx가 직접 서빙 (별도 WAS 없음)
- PeerJS는 Nginx WebSocket 프록시(`/hearbe-peer/`)를 통해 외부 접근
- Backend Security 설정상 일부 엔드포인트가 `permitAll`로 열려 있으므로 운영 정책 검토 필요
- 민감정보는 반드시 `.env` 또는 시크릿 매니저로 분리

### 10-2. AI 서버 (별도)

- AI는 GPU 가속 의존도가 높아 CPU-only 서버에서 성능/지연 저하 가능
- AI compose에 `--reload`가 포함되어 있어 운영 시 비활성 고려
- AI 서버는 메인 웹서버와 독립 운영, Frontend에서 AI 도메인으로 직접 호출

## 11. 발표 기준 이슈 분류 (코드 변경 없이 운영)

### 11-1. 논블로킹 이슈 (발표 핵심 기능 영향 없음)

- `AI/api/http.py`의 일부 상태 조회 엔드포인트(`/api/v1/health/tts`, `/api/v1/config`)는 설정 필드 참조 불일치로 오류 가능성이 있음
  - 2026-02-09 확인: `/api/v1/health/tts` → 500 실제 발생 (예상대로)
- 영향 범위: 상태 조회성 API에 한정
- 비영향 범위: 핵심 데모 플로우(프론트 회원가입 OCR, AI `/api/v1/ocr/welfare-card`, WebSocket `/ws`)는 별도 경로로 동작
- 발표 대응: 상태 조회 API 호출은 생략하고 핵심 플로우 위주로 시연
- WSL2 환경에서 호스트 `nvidia-smi` segfault 발생 (WSL2 알려진 이슈, 컨테이너 내부에서는 정상)

### 11-2. 블로킹 이슈 (발표 전 반드시 확인)

웹서버 측:
- Frontend `.env.production`의 `VITE_OCR_WELFARE_CARD_URL`이 실제 AI 도메인(`your-ai-server.com`)과 불일치하면 OCR 기능 즉시 실패
- Frontend 빌드 시 `.env.production`에 EmailJS 키가 없으면 이메일 인증 실패 가능 (`.env`에만 존재하므로 Vite 빌드 시 자동 머지 여부 확인 필요)
- Nginx PeerJS 프록시(`/hearbe-peer/`) WebSocket 업그레이드 설정 정상 동작 확인

AI 서버 측 (별도 서버에서 확인):
- AI 서버의 Google 서비스계정 JSON 미배치 시 TTS 기능 실패
- AI 서버에서 GPU 미인식 시 ASR/OCR 초기화 지연 또는 실패 가능
- AI 서버 WebSocket(`/ws`) 경로 접근 가능 여부 확인

## 12. 포트/경로 최종 체크표 (발표 전 확인용)

### 12-1. 웹서버 (AWS) 라우팅

| 경로 | 대상 | 비고 |
|---|---|---|
| `https://i14d108.p.ssafy.io` | Frontend 정적 파일 (`dist/`) | Nginx 직접 서빙, SPA 폴백 |
| `https://i14d108.p.ssafy.io/api/*` | Backend `127.0.0.1:8080` | rate-limit 적용 |
| `https://i14d108.p.ssafy.io/hearbe-peer/` | PeerJS `127.0.0.1:9000` | WebSocket 프록시 |

### 12-2. 웹서버 컨테이너 포트

| 서비스 | 호스트:컨테이너 | 비고 |
|---|---|---|
| Backend API | `8080:8080` | `COMPOSE_HOST_PORT` 기본값 |
| MariaDB | `3306:3306` | |
| Redis | `6379:6379` | |
| phpMyAdmin | `8108:80` | |
| PeerJS | `9000:9000` | 경로: `/hearbe-peer` |

### 12-3. AI 서버 (별도)

| 경로 | 대상 | 비고 |
|---|---|---|
| `https://your-ai-server.com/api/v1/ocr/welfare-card` | AI OCR API | Frontend에서 직접 호출 |
| `wss://your-ai-server.com/ws` | AI WebSocket | Frontend에서 직접 호출 |
| AI 내부 컨테이너 | `8000` | |
