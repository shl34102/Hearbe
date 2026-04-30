# Backend 산출물 준비 가이드

## 1. 무엇부터 준비할지 (우선순위)
1. 실행 기준 고정: 런타임 프로필, 포트, 외부 의존성(MariaDB/Redis) 확정
2. 환경변수 표준화: `.env.example` 기준으로 필수/선택 변수 분류
3. 구조/모듈 명세: 패키지 구조와 도메인별 책임(Controller/Service/Repository) 정리
4. 검증 산출물: 기동 체크, 헬스체크, 주요 API 스모크 테스트 결과 수집

## 2. 포트 산출물
| 컴포넌트 | 컨테이너 포트 | 호스트 포트 | 소스 파일 |
|---|---:|---:|---|
| Backend (Spring Boot) | 8080 | `${COMPOSE_HOST_PORT}` | `docker-compose.yml`, `Dockerfile` |
| MariaDB | 3306 | 3306 | `docker-compose.yml` |
| phpMyAdmin | 80 | 8108 | `docker-compose.yml` |
| Redis | 6379 | 6379 | `docker-compose.yml` |
| PeerJS | 9000 | 9000 | `docker-compose.yml` |

## 3. 환경변수 산출물 (필수 중심)
| 범주 | 변수 | 필수 여부 | 설명 |
|---|---|---|---|
| App | `SPRING_APPLICATION_NAME` | 권장 | 애플리케이션 이름 |
| DB | `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD` | 필수 | DB 연결 정보 |
| Redis | `SPRING_DATA_REDIS_HOST`, `SPRING_DATA_REDIS_PORT`, `SPRING_DATA_REDIS_PASSWORD` | 필수 | Redis 연결 정보 |
| Auth | `JWT_SECRET` | 필수 | JWT 서명 키 |
| Auth | `JWT_EXPIRATION` | 선택 | 토큰 만료(ms), 기본값 존재 |
| Crypto | `ENCRYPTION_SECRET_KEY` | 필수 | AES 암복호화 키 |
| Mail | `SPRING_MAIL_*` | 필수(메일 기능 사용 시) | SMTP 설정 |
| OpenVidu | `OPENVIDU_URL`, `OPENVIDU_SECRET` | 선택(해당 기능 사용 시) | 화상/세션 관련 |
| Compose | `COMPOSE_HOST_PORT`, `COMPOSE_HOST_LOG_PATH`, `COMPOSE_APP_PROFILE` | 권장 | 실행 환경 설정 |
| Infra | `MYSQL_*`, `PMA_*`, `REDIS_PASSWORD` | 필수(Docker Compose 기준) | 인프라 컨테이너 설정 |

참고: 실제 키/비밀번호는 `.env`에만 두고, 배포 시에는 시크릿 매니저 사용을 권장합니다.

## 4. 구조/모듈 산출물
현재 주요 모듈 구조:
- `auth`: 인증/회원관리
- `member`: 프로필/복지카드
- `cartItem`: 장바구니
- `wishlist`: 위시리스트
- `order`: 주문
- `platform`: 플랫폼 데이터
- `global`: 보안, 예외, 응답 포맷, 공통 유틸
- `entity`: JPA 엔티티 및 enum

권장 산출물 형식:
1. 모듈 책임표: 모듈별 Controller/Service/Repository/Entity 연결
2. 의존성 다이어그램: 요청 흐름(Controller -> Service -> Repository)
3. 외부 연동표: DB/Redis/OpenVidu/메일 연동 지점

## 5. 바로 제출 가능한 산출물 패키지
1. `PORTS.md`: 포트 매핑 및 접근 URL
2. `ENVIRONMENT_VARIABLES.md`: 변수명/필수여부/예시/보안등급
3. `ARCHITECTURE.md`: 패키지 구조와 모듈 책임
4. `MODULE_SPEC.md`: 모듈별 API/DTO/예외/테스트 범위
5. `RUNBOOK.md`: 기동/중지/장애 확인 절차

## 6. 추천 진행 순서 (실행 기준)
1. `.env.example` 기반으로 팀 공통 변수 확정
2. `docker-compose.yml` 기준 포트/프로필 표 확정
3. 모듈 책임표(현재 패키지 기준) 작성
4. 헬스체크(`/health`) + 핵심 API 스모크 테스트 결과 첨부
