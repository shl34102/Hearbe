# 로깅 정책 (AI 서비스)

## 목표

* 하나의 환경 스위치로 local/dev/prod 전 구간에서 로그 정책을 일관되게 유지한다.
* 일 단위 로그 로테이션(회전)을 사용하고, 보관 기간(retention)을 제한한다.
* 파일 이름과 로그 타임스탬프 모두 **UTC**를 기준으로 사용한다.

---

## AI 서비스 (Python/FastAPI)

### 로그 저장 위치

* 컨테이너 경로: `/app/logs`
* 호스트 경로(compose): `./logs` → `S14P11D108/AI/logs`

### 로테이션 및 보관(retention)

* `TimedRotatingFileHandler`를 사용해 **매일 자정(midnight) 기준으로 로테이션**한다.
* 일별 로그 파일은 동일한 logs 디렉터리에 저장된다.
* 보관 기간은 `LOG_BACKUP_COUNT`로 제어한다.

### 타임존

* `LOG_ROTATE_UTC=true`는 아래 두 가지를 모두 강제한다:

  * 로테이션 기준 시간
  * 로그 타임스탬프를 UTC로 기록

### APP_ENV 프로필 선택 및 오버라이드(override)

* `APP_ENV`가 기본 프로필을 선택한다: `DEV_*` 또는 `PROD_*`
* 어떤 `LOG_*` 또는 `DEBUG` 값이든 **프로필 값을 덮어쓴다**.

우선순위(위가 가장 강함):

1. `LOG_*` 및 `DEBUG`
2. `APP_ENV`에 따른 `DEV_*` / `PROD_*`
3. 코드 기본값(code defaults)

### 예시 .env

```dotenv
APP_ENV=prod

# PROD profile
PROD_DEBUG=false
PROD_LOG_LEVEL=INFO
PROD_LOG_CONSOLE_LEVEL=WARNING
PROD_LOG_FILE_LEVEL=INFO
PROD_LOG_DIR=logs
PROD_LOG_FILE=ai_server.log
PROD_LOG_ROTATE_WHEN=midnight
PROD_LOG_ROTATE_INTERVAL=1
PROD_LOG_BACKUP_COUNT=30
PROD_LOG_ROTATE_UTC=true

# Optional overrides
LOG_CONSOLE_LEVEL=ERROR
```

### 예시 파일명

* 현재 파일: `logs/ai_server.log`
* 일별 로테이션 파일: `logs/ai_server.log.YYYY-MM-DD.log`

---

### 로테이션 및 보관(retention)

* `TimeBasedRollingPolicy`로 **일 단위 로테이션**한다.
* 파일 패턴: `logs/backend-YYYY-MM-DD.log`
* 보관 기간: `LOG_MAX_HISTORY`

### 타임존

* `LOG_TIMEZONE=UTC`가 아래를 제어한다:

  * 로그 타임스탬프
  * 일별 파일명 생성 기준 타임존

### 예시 application.properties

```properties
logging.config=classpath:logback-spring.xml
LOG_LEVEL=INFO
LOG_CONSOLE_LEVEL=
LOG_FILE_LEVEL=
LOG_DIR=logs
LOG_FILE=backend.log
LOG_MAX_HISTORY=7
LOG_TIMEZONE=UTC
```

---

## 운영 메모

* 전 구간에서 UTC를 사용하면 local과 서버 간 날짜가 어긋나는 문제(date skew)를 방지할 수 있다.
* 필요 시, 백엔드는 `LOG_TIMEZONE`, AI는 `LOG_ROTATE_UTC`를 변경해서 기준을 전환할 수 있다.
* 로그 저장 위치를 바꾸려면 `LOG_DIR`을 변경하고, compose 볼륨 매핑도 함께 조정한다.
