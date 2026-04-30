package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 공유 세션이 만료되었을 때 발생하는 예외
 */
public class SessionExpiredException extends BusinessException {

    public SessionExpiredException() {
        super(ErrorCode.SESSION_EXPIRED);
    }

    public SessionExpiredException(String meetingCode) {
        super(ErrorCode.SESSION_EXPIRED, "공유 세션이 만료되었습니다. 미팅 코드: " + meetingCode);
    }
}
