package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 사용자 중복 예외
 * 회원가입 시 이미 존재하는 아이디로 가입하려 할 때 발생
 */
public class DuplicateUserException extends BusinessException {

    public DuplicateUserException() {
        super(ErrorCode.DUPLICATE_USER);
    }

    public DuplicateUserException(String username) {
        super(ErrorCode.DUPLICATE_USER, "이미 사용 중인 아이디입니다: " + username);
    }
}
