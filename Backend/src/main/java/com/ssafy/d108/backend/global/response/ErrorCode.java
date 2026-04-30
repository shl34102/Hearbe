package com.ssafy.d108.backend.global.response;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

import java.util.Optional;
import java.util.function.Predicate;

/**
 * 에러 코드 정의 Enum
 * HTTP 상태 코드와 유사한 3-4자리 커스텀 에러 코드 사용
 */
@Getter
@RequiredArgsConstructor
public enum ErrorCode {

    /**
     * ============================================================
     * 성공 응답 (200번대)
     * ============================================================
     */
    SUCCESS(HttpStatus.OK, 200, "성공적으로 처리되었습니다."),
    CREATED(HttpStatus.CREATED, 201, "성공적으로 생성되었습니다."),

    /**
     * ============================================================
     * 클라이언트 에러 - 잘못된 요청 (400번대)
     * ============================================================
     */
    INVALID_INPUT(HttpStatus.BAD_REQUEST, 400, "잘못된 입력값입니다."),
    VALIDATION_ERROR(HttpStatus.BAD_REQUEST, 4001, "입력값 검증에 실패했습니다."),
    NULL_INPUT_VALUE(HttpStatus.BAD_REQUEST, 4002, "필수 입력값이 누락되었습니다."),
    INVALID_FILE_EXTENSION(HttpStatus.BAD_REQUEST, 4003, "지원하지 않는 파일 형식입니다."),
    INVALID_PASSWORD(HttpStatus.BAD_REQUEST, 4004, "비밀번호가 일치하지 않습니다."),
    PLATFORM_SYNC_FAILED(HttpStatus.BAD_REQUEST, 4005, "쇼핑몰 연동에 실패했습니다. 잠시 후 다시 시도해주세요."),
    PAYMENT_FAILED(HttpStatus.BAD_REQUEST, 4006, "결제에 실패했습니다."),
    PAYMENT_CANCELLED(HttpStatus.BAD_REQUEST, 4007, "결제가 취소되었습니다."),
    INSUFFICIENT_STOCK(HttpStatus.BAD_REQUEST, 4008, "상품 재고가 부족합니다."),
    INVALID_MEETING_CODE(HttpStatus.BAD_REQUEST, 4009, "유효하지 않은 미팅 코드입니다."),
    SESSION_ALREADY_ENDED(HttpStatus.BAD_REQUEST, 4010, "이미 종료된 세션입니다."),
    WELFARE_CARD_VERIFICATION_FAILED(HttpStatus.BAD_REQUEST, 4011, "복지카드 인증에 실패했습니다."),
    INVALID_WELFARE_CARD(HttpStatus.BAD_REQUEST, 4012, "유효하지 않은 복지카드입니다."),

    /**
     * ============================================================
     * 클라이언트 에러 - 인증 필요 (401번대)
     * ============================================================
     */
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, 401, "인증이 필요합니다. 로그인 후 이용해주세요."),
    INVALID_TOKEN(HttpStatus.UNAUTHORIZED, 4011, "유효하지 않은 토큰입니다."),
    EXPIRED_TOKEN(HttpStatus.UNAUTHORIZED, 4012, "토큰이 만료되었습니다. 다시 로그인해주세요."),

    /**
     * ============================================================
     * 클라이언트 에러 - 권한 없음 (403)
     * ============================================================
     */
    ACCESS_DENIED(HttpStatus.FORBIDDEN, 403, "접근 권한이 없습니다."),

    /**
     * ============================================================
     * 클라이언트 에러 - 찾을 수 없음 (404번대)
     * ============================================================
     */
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, 4041, "사용자를 찾을 수 없습니다."),
    PRODUCT_NOT_FOUND(HttpStatus.NOT_FOUND, 4042, "상품을 찾을 수 없습니다."),
    PLATFORM_NOT_FOUND(HttpStatus.NOT_FOUND, 4043, "플랫폼을 찾을 수 없습니다."),
    CART_ITEM_NOT_FOUND(HttpStatus.NOT_FOUND, 4044, "장바구니에서 상품을 찾을 수 없습니다."),
    WISHLIST_ITEM_NOT_FOUND(HttpStatus.NOT_FOUND, 4045, "찜한 상품을 찾을 수 없습니다."),
    ORDER_NOT_FOUND(HttpStatus.NOT_FOUND, 4046, "주문 내역을 찾을 수 없습니다."),
    SESSION_NOT_FOUND(HttpStatus.NOT_FOUND, 4047, "공유 세션을 찾을 수 없습니다."),

    /**
     * ============================================================
     * 클라이언트 에러 - 중복/충돌 (409번대)
     * ============================================================
     */
    DUPLICATE_USER(HttpStatus.CONFLICT, 4091, "이미 존재하는 아이디입니다."),
    DUPLICATE_LOGIN_ID(HttpStatus.CONFLICT, 4092, "이미 사용 중인 로그인 아이디입니다."),
    ALREADY_IN_WISHLIST(HttpStatus.CONFLICT, 4093, "이미 찜한 상품입니다."),

    /**
     * ============================================================
     * 클라이언트 에러 - 만료됨 (410)
     * ============================================================
     */
    SESSION_EXPIRED(HttpStatus.GONE, 410, "공유 세션이 만료되었습니다."),

    /**
     * ============================================================
     * 서버 에러 (500번대)
     * ============================================================
     */
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, 500, "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."),
    OCR_PROCESSING_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, 5001, "이미지 인식에 실패했습니다. 다시 시도해주세요."),
    DATABASE_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, 5002, "데이터베이스 오류가 발생했습니다."),
    REDIS_CONNECTION_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, 5003, "캐시 서버 연결에 실패했습니다."),

    /**
     * ============================================================
     * 서버 에러 - 서비스 이용 불가 (503)
     * ============================================================
     */
    EXTERNAL_API_ERROR(HttpStatus.SERVICE_UNAVAILABLE, 503, "외부 서비스 연동 중 오류가 발생했습니다.");

    private final HttpStatus status;
    private final Integer code;
    private final String message;

    /**
     * 예외 메시지와 함께 커스텀 메시지 생성
     */
    public String getMessage(Throwable e) {
        return this.getMessage(this.getMessage() + " - " + e.getMessage());
    }

    /**
     * 커스텀 메시지가 있으면 사용하고, 없으면 기본 메시지 반환
     */
    public String getMessage(String message) {
        return Optional.ofNullable(message)
                .filter(Predicate.not(String::isBlank))
                .orElse(this.getMessage());
    }

    /**
     * 상세 메시지 조합
     */
    public String getDetailMessage(String message) {
        return this.getMessage() + " : " + message;
    }
}
