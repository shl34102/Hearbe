# Entity 생성자 리팩토링 가이드

> **작성일**: 2026-02-05  
> **목적**: JPA Entity의 불변성, 캡슐화, 테스트 용이성 개선

---

## � 현재 상태

### ✅ 적절한 Entity

| Entity | 상태 |
|--------|------|
| **Platform** | `@NoArgsConstructor(PROTECTED)` + 비즈니스 생성자 존재 ✅ |

### ⚠️ 개선 필요 Entity

| Entity | 현재 문제 |
|--------|----------|
| User | `@NoArgsConstructor(public)` + `@Setter` |
| Profile | `@NoArgsConstructor(public)` + `@Setter` |
| Order | `@NoArgsConstructor(public)` + `@Setter` |
| CartItem | `@NoArgsConstructor(public)` + `@Setter` |
| OrderItem | `@NoArgsConstructor(public)` + `@Setter` |
| WelfareCard | `@NoArgsConstructor(public)` + `@Setter` |
| WishlistItem | `@NoArgsConstructor(public)` + `@Setter` |
| SharingSessionLog | `@NoArgsConstructor(public)` |

---

## 🔍 문제점

### 1. 캡슐화 위반
- Public 기본 생성자로 인해 필수 필드 없이 Entity 생성 가능
- 런타임에 예외 발생 가능

### 2. 비즈니스 로직 검증 불가
- Setter를 통한 직접 수정으로 음수 수량, 음수 가격 등 비정상 데이터 입력 가능

### 3. 테스트 코드 복잡도 증가
- Entity 생성 시 다수의 setter 호출 필요
- 필수 필드 누락 가능성

---

## ✨ 권장 개선 사항

### 핵심 원칙

1. **JPA용 기본 생성자는 `protected`로 제한**
   ```java
   @NoArgsConstructor(access = AccessLevel.PROTECTED)
   ```

2. **비즈니스 생성자 또는 Builder 패턴 추가**
   - 필드 3개 이하: 생성자
   - 필드 4개 이상: `@Builder`

3. **Setter 제거 또는 최소화**
   - 명시적 업데이트 메서드로 대체
   - 비즈니스 규칙 검증 포함

---

## 📋 Entity별 개선 방안

### 1. User
- **필수 필드**: `username`, `userType`
- **권장**: `@Builder` 패턴
- **업데이트 메서드**: `updateProfile(email, phoneNumber, name)`

### 2. Profile
- **필수 필드**: `user`
- **권장**: 생성자 `Profile(User user)`
- **업데이트 메서드**: 
  - `updatePhysicalInfo(height, weight, topSize, bottomSize, shoeSize)`
  - `updateAllergies(allergies, etcAllergy)`

### 3. Order
- **필수 필드**: `user`
- **권장**: 생성자 `Order(User user)` 또는 정적 팩토리 메서드
- **업데이트 메서드**: `updateUrls(orderDetailUrl, deliveryUrl)`

### 4. CartItem ⭐ (우선순위 High)
- **필수 필드**: `user`, `platform`, `name`, `price`
- **권장**: `@Builder` 패턴
- **업데이트 메서드**: 
  - `updateQuantity(quantity)` - 1 이상 검증
  - `updatePrice(price)` - 0 이상 검증
- **정적 팩토리**: `create(user, platform, name, price)`

### 5. OrderItem ⭐ (우선순위 High)
- **필수 필드**: `order`, `user`, `platform`, `name`, `price`
- **권장**: `@Builder` 패턴
- **정적 팩토리**: `fromCartItem(Order order, CartItem cartItem)`
- **업데이트 메서드**: `updateDeliveryUrl(deliverUrl)`

### 6. WelfareCard ⭐ (우선순위 High)
- **필수 필드**: `user`, `cardNumber`, `expirationDate`
- **권장**: `@Builder` 패턴
- **업데이트 메서드**: `updateCardInfo(cardNumber, expirationDate, cvc)`

### 7. WishlistItem
- **필수 필드**: `user`, `platform`, `name`, `price`
- **권장**: `@Builder` 패턴
- **업데이트 메서드**: `updateQuantity(quantity)` - 1 이상 검증

### 8. SharingSessionLog
- **필수 필드**: `hostUser`, `meetingCode`
- **권장**: `@Builder` 패턴
- **업데이트 메서드**: `endSession()` - endedAt 설정, status 변경

---

## 🎯 우선순위

### High - 즉시 적용 권장
비즈니스 로직이 복잡하고 검증이 필요한 Entity

- CartItem (수량/가격 검증)
- OrderItem (주문 데이터 무결성)
- WelfareCard (카드 정보 보안)

### Medium - 점진적 적용
핵심 도메인 Entity

- User (사용자 필수 정보)
- Profile (프로필 관리)
- Order (주문 관리)

### Low - 선택적 적용
상대적으로 단순한 Entity

- WishlistItem
- SharingSessionLog

---

## 🔄 마이그레이션 전략

### 단계별 적용

1. **1단계**: `@NoArgsConstructor(PROTECTED)` + `@Builder` 추가
   - 기존 코드에 영향 없음

2. **2단계**: Service Layer에서 Builder 패턴으로 변경
   - 점진적으로 setter 호출 → builder 사용

3. **3단계**: 모든 변경 완료 후 `@Setter` 제거 검토

### 예시

#### Before
```java
CartItem item = new CartItem();
item.setUser(user);
item.setPlatform(platform);
item.setName("상품명");
item.setPrice(10000L);
```

#### After
```java
CartItem item = CartItem.builder()
    .user(user)
    .platform(platform)
    .name("상품명")
    .price(10000L)
    .build();
```

---

## 📌 체크리스트

적용 시 확인 사항:

- [ ] `@NoArgsConstructor(access = AccessLevel.PROTECTED)` 추가
- [ ] `@Builder` 또는 비즈니스 생성자 추가
- [ ] 필수 필드를 생성자/Builder 파라미터로 설정
- [ ] Setter를 명시적 업데이트 메서드로 대체
- [ ] 업데이트 메서드에 비즈니스 규칙 검증 추가
- [ ] Service Layer 코드 수정
- [ ] 관련 테스트 코드 업데이트 및 실행
- [ ] 팀원과 변경사항 공유

---

## 📚 참고

- JPA는 리플렉션으로 Entity를 생성하므로 기본 생성자는 `protected`면 충분
- Builder 패턴은 필드가 많을 때 가독성과 유지보수성 향상
- 정적 팩토리 메서드는 비즈니스 의미를 명확히 표현 가능
