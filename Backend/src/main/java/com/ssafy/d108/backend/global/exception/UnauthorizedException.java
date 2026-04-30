package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 인증 실패 예외
 * 로그인하지 않았거나 토큰이 유효하지 않을 때 발생
 */
public class UnauthorizedException extends BusinessException {

    public UnauthorizedException() {
        super(ErrorCode.UNAUTHORIZED);
    }

    public UnauthorizedException(String message) {
        super(ErrorCode.UNAUTHORIZED, message);
    }

    public UnauthorizedException(Throwable cause) {
        super(ErrorCode.UNAUTHORIZED, cause);
    }
}
