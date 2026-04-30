package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 결제 실패 예외
 * 결제 처리 중 오류가 발생했을 때 사용
 */
public class PaymentFailedException extends BusinessException {

    public PaymentFailedException() {
        super(ErrorCode.PAYMENT_FAILED);
    }

    public PaymentFailedException(String message) {
        super(ErrorCode.PAYMENT_FAILED, message);
    }

    public PaymentFailedException(String message, Throwable cause) {
        super(ErrorCode.PAYMENT_FAILED, message, cause);
    }
}
