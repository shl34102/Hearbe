# Logging Configuration Guide

HEARBE 백엔드 애플리케이션의 로깅 설정 가이드입니다.

## 개요

로깅은 **`logback-spring.xml`** 파일에서 설정합니다. Spring Profile(dev/prod)에 따라 자동으로 다른 로그 레벨과 출력 방식이 적용됩니다.

---

## 로그 레벨

### 로그 레벨 우선순위
```
TRACE < DEBUG < INFO < WARN < ERROR
```

레벨을 `INFO`로 설정하면: `INFO`, `WARN`, `ERROR`만 출력 (TRACE, DEBUG는 제외)

### 각 레벨의 용도

| 레벨 | 용도 | 예시 |
|-----|------|-----|
| **TRACE** | 가장 상세한 정보 | SQL 파라미터 값, 메서드 진입/종료 |
| **DEBUG** | 개발/디버깅 정보 | SQL 쿼리, 중요 변수 값 |
| **INFO** | 일반 정보 (정상 흐름) | 서버 시작, API 호출 성공, 사용자 로그인 |
| **WARN** | 경고 (주의 필요) | **유효성 검사 실패**, Deprecated 사용, 재시도 |
| **ERROR** | 오류 (시스템 문제) | 예외 발생, DB 연결 실패, NPE |

---

## 코드에서 로그 사용하기

### 올바른 로그 레벨 선택

```java
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class UserService {
    
    public void registerUser(UserRequest request) {
        // ✅ INFO: 정상 흐름
        log.info("회원가입 시작: username={}", request.getUsername());
        
        // ✅ WARN: 유효성 검사 실패 (비즈니스 룰 위반)
        if (!isValidEmail(request.getEmail())) {
            log.warn("유효성 검사 실패: 이메일 형식 오류 - email={}", request.getEmail());
            throw new ValidationException("Invalid email format");
        }
        
        // ✅ DEBUG: 개발 시에만 필요한 상세 정보
        log.debug("사용자 정보 저장 전 - request={}", request);
        
        try {
            userRepository.save(user);
            // ✅ INFO: 성공
            log.info("회원가입 완료: userId={}", user.getId());
        } catch (DataAccessException e) {
            // ✅ ERROR: 시스템 오류
            log.error("DB 저장 실패: username={}", request.getUsername(), e);
            throw new DatabaseException("Failed to save user", e);
        }
    }
    
    // ✅ TRACE: 매우 상세한 정보 (개발 시에만)
    private void validatePassword(String password) {
        log.trace("비밀번호 검증 시작: length={}", password.length());
        // ...
    }
}
```

### 트러블슈팅 시나리오별 로그 레벨

| 상황 | 레벨 | 예시 |
|-----|------|-----|
| 유효성 검사 실패 | WARN | 이메일 형식 오류, 필수 필드 누락 |
| 권한 부족 | WARN | 관리자 권한 필요, 본인 데이터 아님 |
| 비즈니스 룰 위반 | WARN | 중복 회원가입, 재고 부족 |
| 외부 API 재시도 | WARN | 결제 API 타임아웃, 재시도 중 |
| 시스템 예외 | ERROR | DB 연결 실패, NPE, 파일 읽기 실패 |
| 치명적 오류 | ERROR | 서버 기동 실패, 설정 오류 |

---

## ⚠️ 유효성 검사 로그 추적하기

### 명확한 답변: **Java 코드 수정 없이 가능합니다**

Spring Boot가 이미 유효성 검사 실패 시 자동으로 로그를 남깁니다. `logback-spring.xml`에서 해당 로거만 활성화하면 됩니다.

### 방법 1: XML 설정만 추가 (추천 ⭐)

**logback-spring.xml에 딱 한 줄만 추가:**

```xml
<springProfile name="dev">
    <!-- Spring의 유효성 검사 예외 로그 활성화 -->
    <logger name="org.springframework.web.servlet.mvc.support.DefaultHandlerExceptionResolver" level="WARN" />
</springProfile>
```

**효과:**
- ✅ 유효성 검사 실패 시 자동 로그 출력
- ✅ Java 코드 단 한 줄도 수정 안 해도 됨
- ✅ Spring이 알아서 예외 정보를 로그로 남김

**로그 예시:**
```
2026-02-11 15:30:47.123 [http-nio-8080-exec-1] WARN org.springframework.web.servlet.mvc.support.DefaultHandlerExceptionResolver - Resolved [org.springframework.web.bind.MethodArgumentNotValidException: Validation failed for argument [0] in public org.springframework.http.ResponseEntity...]
```

---

### 방법 2: Grafana에서 검색으로 해결 (설정 변경 X)

유효성 검사가 실패하면 **HTTP 상태 코드가 400 (Bad Request)**으로 자동 응답됩니다.

**Grafana Explore에서:**

```logql
# 400 에러만 보기
{job="hearbe-backend"} |= "400"

# Bad Request 검색
{job="hearbe-backend"} |= "Bad Request"

# 유효성 검사 예외 검색
{job="hearbe-backend"} |= "MethodArgumentNotValidException"
```

---

### 방법 3: 명시적 로그 추가 (선택)

더 명확한 메시지가 필요하다면 Java 코드에 직접 로그를 추가할 수도 있습니다.

```java
@Slf4j
@PostMapping("/register")
public ResponseEntity<?> register(@Valid @RequestBody UserRequest request) {
    if (userService.existsByEmail(request.getEmail())) {
        log.warn("유효성 검사 실패: 이메일 중복 - email={}", request.getEmail());
        throw new DuplicateEmailException();
    }
    return ResponseEntity.ok(userService.register(request));
}
```

**추천:** 처음에는 방법 1이나 2로 시작하고, 나중에 필요하면 방법 3 적용

---

## 환경별 로그 설정

### 개발 환경 (dev)

**특징:**
- 콘솔 + 파일 모두 출력
- SQL 쿼리 및 파라미터 출력
- 우리 코드(com.ssafy.d108)는 DEBUG 레벨

**적용 방법:**
```bash
# .env 파일
COMPOSE_APP_PROFILE=dev
```

**로그 출력:**
```
2026-02-11 15:30:45.123 [main] INFO  com.ssafy.d108.Application - 서버 시작
2026-02-11 15:30:46.456 [http-nio-8080-exec-1] DEBUG com.ssafy.d108.service.UserService - 회원가입 요청: user=test@test.com
2026-02-11 15:30:46.789 [http-nio-8080-exec-1] DEBUG org.hibernate.SQL - insert into users (email, password) values (?, ?)
2026-02-11 15:30:46.790 [http-nio-8080-exec-1] TRACE org.hibernate.type.descriptor.sql.BasicBinder - binding parameter [1] as [VARCHAR] - [test@test.com]
2026-02-11 15:30:47.000 [http-nio-8080-exec-1] WARN  com.ssafy.d108.controller.UserController - 유효성 검사 실패: 이메일 중복
```

**설정 방법:**

1. `.env` 파일 열기
```bash
vi .env
```

2. 프로파일을 dev로 설정
```properties
# .env 파일
COMPOSE_APP_PROFILE=dev
COMPOSE_HOST_PORT=8080
```

3. Docker Compose 재시작
```bash
docker-compose down
docker-compose up -d --build
```


---

### 운영 환경 (prod)

**특징:**
- 콘솔 + 파일 모두 출력
- SQL 쿼리 숨김
- WARN 이상만 출력 (INFO, DEBUG, TRACE 제외)
- 우리 코드는 INFO 레벨

**적용 방법:**
```bash
# .env 파일
COMPOSE_APP_PROFILE=prod
```

**로그 출력:**
```
2026-02-11 15:30:45.123 [main] INFO  com.ssafy.d108.Application - 서버 시작
2026-02-11 15:30:47.000 [http-nio-8080-exec-1] WARN  com.ssafy.d108.controller.UserController - 유효성 검사 실패: 이메일 중복
2026-02-11 15:31:00.000 [http-nio-8080-exec-5] ERROR com.ssafy.d108.service.PaymentService - 결제 API 호출 실패
```

**설정 방법:**

1. `.env` 파일 열기
```bash
vi .env
```

2. 프로파일을 prod로 설정
```properties
# .env 파일
COMPOSE_APP_PROFILE=prod
COMPOSE_HOST_PORT=80
```

3. Docker Compose 재시작
```bash
docker-compose down
docker-compose up -d --build
```

> [!WARNING]
> 운영 환경 배포 전 반드시 확인:
> - `COMPOSE_APP_PROFILE=prod` 설정 확인
> - 모든 민감한 정보(DB 비밀번호, JWT_SECRET 등) 변경
> - `logback-spring.xml`의 prod 프로파일이 WARN 레벨인지 확인

---

## logback-spring.xml 상세 설정

### 전체 구조

render_diffs(file:///c:/Users/SSAFY/Desktop/main_integration/Backend/src/main/resources/logback-spring.xml)

### Package별 로거 설정

```xml
<!-- 우리 애플리케이션 코드 -->
<logger name="com.ssafy.d108" level="DEBUG" />

<!-- 특정 패키지만 더 상세히 -->
<logger name="com.ssafy.d108.service.PaymentService" level="TRACE" />

<!-- SQL 쿼리 -->
<logger name="org.hibernate.SQL" level="DEBUG" />

<!-- SQL 파라미터 값 -->
<logger name="org.hibernate.type.descriptor.sql.BasicBinder" level="TRACE" />

<!-- Spring Security (인증/인가) -->
<logger name="org.springframework.security" level="INFO" />

<!-- Spring Web (HTTP 요청) -->
<logger name="org.springframework.web" level="DEBUG" />
```

---

## 로그 파일 관리

### 파일 저장 위치

- **컨테이너 내부**: `/logs/app.log`
- **호스트**: `./logs/app.log` (docker-compose.yml 설정)

### 로그 롤링 정책

```xml
<rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
    <fileNamePattern>${LOG_FILE}.%d{yyyy-MM-dd}.gz</fileNamePattern>
    <maxHistory>30</maxHistory>
</rollingPolicy>
```

- 매일 자정에 로그 파일 롤링 (gzip 압축)
- 최근 30일치만 보관
- 예: `app.log.2026-02-10.gz`, `app.log.2026-02-11.gz`

### 로그 확인 방법

```bash
# 실시간 로그 (콘솔)
docker logs -f hearbe-backend

# 파일 로그 확인
docker exec hearbe-backend tail -f /logs/app.log

# 호스트에서 파일 확인
cat ./logs/app.log

# Grafana + Loki로 확인 (권장)
http://localhost:3000
```

---

## Grafana + Loki 로그 모니터링

### 로그 쿼리 예시

**전체 로그:**
```logql
{job="hearbe-backend"}
```

**ERROR 로그만:**
```logql
{job="hearbe-backend"} |= "ERROR"
```

**유효성 검사 실패만:**
```logql
{job="hearbe-backend"} |= "유효성 검사 실패"
```

**특정 서비스 로그:**
```logql
{job="hearbe-backend", logger="com.ssafy.d108.service.UserService"}
```

**시간별 에러 개수:**
```logql
sum(count_over_time({job="hearbe-backend"} |= "ERROR" [1m]))
```

---

## 로그 레벨 변경하기

### 일시적 변경 (재시작 필요)

`logback-spring.xml` 수정 후 컨테이너 재시작:

```bash
# 1. logback-spring.xml 수정
vi src/main/resources/logback-spring.xml

# 2. Docker 이미지 재빌드
docker-compose up -d --build
```

### 특정 패키지만 변경

```xml
<!-- UserService만 TRACE 레벨로 -->
<logger name="com.ssafy.d108.service.UserService" level="TRACE" />
```

---

## Best Practices

### ✅ DO

```java
// 구조화된 로그 (변수 포함)
log.info("회원가입 완료: userId={}, email={}", user.getId(), user.getEmail());

// 예외는 마지막 파라미터로
log.error("결제 실패: orderId={}", orderId, exception);

// 유효성 검사 실패는 WARN
log.warn("유효성 검사 실패: 잘못된 이메일 형식 - {}", email);
```

### ❌ DON'T

```java
// 문자열 연결 (성능 저하)
log.debug("User: " + user.getName() + ", Age: " + user.getAge());

// 민감한 정보 노출
log.info("비밀번호: {}", password);  // ❌

// 시스템 오류가 아닌데 ERROR 사용
log.error("이메일 형식 오류");  // ❌ WARN 사용해야 함
```

---

## 주의사항

> [!WARNING]
> **운영 환경 주의사항**
> - DEBUG/TRACE 레벨 사용 금지 (성능 저하, 디스크 full)
> - 민감한 정보(비밀번호, 토큰) 로그 출력 금지
> - SQL 쿼리 로그 비활성화 (보안, 성능)

> [!IMPORTANT]
> **유효성 검사 로그 레벨**
> - 유효성 검사 실패: **WARN** (비즈니스 룰 위반)
> - 시스템 예외: **ERROR** (DB 오류, NPE 등)
> - 정상 흐름: **INFO** (로그인 성공, 등록 완료)

> [!TIP]
> **디버깅 팁**
> - 특정 기능 문제 시 해당 패키지만 DEBUG로 변경
> - Grafana에서 `|= "WARN"` 또는 `|= "ERROR"`로 필터링
> - 운영 문제 발생 시 최근 ERROR 로그부터 확인
