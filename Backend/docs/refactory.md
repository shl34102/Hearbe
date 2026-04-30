# Refactoring Log - 2026-02-05

> **작업 일시**: 2026-02-05  
> **목적**: 백엔드 코드의 일관성 유지, 중복 제거 및 유지보수성 향상을 위한 리팩토링 내역

---

## 1. DTO 리팩토링 (Lombok 및 생성자 패턴)

DTO 객체의 안정적인 직렬화/역직렬화와 개발 생산성 향상을 위해 리팩토링을 진행했습니다.

### ✅ **주요 수정 사항**
- **역직렬화 오류 해결**: `CartItemCreateResponse` 등 일부 Response DTO에 `@NoArgsConstructor`가 누락되어 Jackson이 객체를 생성하지 못하는 문제를 해결했습니다.
- **Lombok 전환**: `WelfareCardRequest`와 같이 수동으로 구현된 약 100줄의 Getter/Setter/생성자 코드를 Lombok 어노테이션으로 교체하여 가독성을 높였습니다.
- **테스트 편의성 개선**: Request DTO들에 `@AllArgsConstructor`를 추가하여 테스트 코드에서 `new` 키워드로 간편하게 객체를 생성할 수 있도록 지원했습니다.

---

## 2. Controller & Service 공통 로직 리팩토링

반복되는 인증 정보 추출 로직을 유틸리티로 공통화하여 코드 중복을 제거했습니다.

### ✅ **주요 수정 사항**
- **인증 방식 일원화 (`SecurityUtil`)**:
  - 기존: 컨트롤러마다 `Authentication` 객체를 직접 캐스팅하여 `userId` 추출
  - 수정: `SecurityUtil.getCurrentUserId()` 공통 메서드 호출 방식으로 변경
- **적용 대상**: `ProfileController`, `CartItemController` 등 회원 정보가 필요한 전방위 컨트롤러 및 서비스

---

## 3. Test Code 리팩토링 및 검증

변경된 공통 로직이 테스트 환경에서도 정상 작동하도록 보완했습니다.

### ✅ **주요 수정 사항**
- **ProfileControllerTest 정상화**:
  - **경로 수정**: 컨트롤러 매핑 주소와 일치하도록 `/api/members` 경로에서 `/members`로 수정했습니다.
  - **인증 셋업**: `SecurityUtil`이 테스트 환경에서도 `userId`를 정상적으로 반환할 수 있도록 `SecurityContextHolder`에 인증 정보를 수동으로 주입하는 로직을 추가했습니다.
- **결과**: 관련 API 테스트가 성공적으로 통과됨을 확인했습니다.

---

## 📊 리팩토링 요약 표

| 영역 | 대상 | 주요 리팩토링 내용 |
| :--- | :--- | :--- |
| **DTO** | `CartItemCreateResponse`, `WelfareCardRequest` 등 | `@NoArgsConstructor`, `@AllArgsConstructor` 추가 및 Lombok 적용 |
| **Common** | `SecurityUtil` 도입 | `getCurrentUserId()`를 통한 인증 정보 추출 로직 공통화 |
| **Test** | `ProfileControllerTest` | 요청 경로 정상화 및 SecurityContext Mocking 보완 |

---

## 🔗 관련 분석 문서
- [DTO 분석 보고서](file:///c:/Users/SSAFY/Desktop/main_integration/Backend/docs/dto_analysis.md)
- [Entity 생성자 리팩토링 가이드](file:///c:/Users/SSAFY/Desktop/main_integration/Backend/docs/entity_constructor_refactoring.md)
