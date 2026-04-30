package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 복지카드 인증 실패 예외
 * 장애인 복지카드 OCR 인증 중 오류가 발생했을 때 사용
 */
public class WelfareCardVerificationException extends BusinessException {

    public WelfareCardVerificationException() {
        super(ErrorCode.WELFARE_CARD_VERIFICATION_FAILED);
    }

    public WelfareCardVerificationException(String message) {
        super(ErrorCode.WELFARE_CARD_VERIFICATION_FAILED, message);
    }

    public WelfareCardVerificationException(String message, Throwable cause) {
        super(ErrorCode.WELFARE_CARD_VERIFICATION_FAILED, message, cause);
    }
}
