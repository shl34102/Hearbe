package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 비밀번호 불일치 예외
 * 로그인 시 비밀번호가 틀렸거나 비밀번호 변경 시 현재 비밀번호가 틀렸을 때 발생
 */
public class InvalidPasswordException extends BusinessException {

    public InvalidPasswordException() {
        super(ErrorCode.INVALID_PASSWORD);
    }

    public InvalidPasswordException(String message) {
        super(ErrorCode.INVALID_PASSWORD, message);
    }
}
