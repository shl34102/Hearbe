package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 공유 세션을 찾을 수 없을 때 발생하는 예외
 */
public class SessionNotFoundException extends BusinessException {

    public SessionNotFoundException() {
        super(ErrorCode.SESSION_NOT_FOUND);
    }

    public SessionNotFoundException(Integer sessionId) {
        super(ErrorCode.SESSION_NOT_FOUND, "공유 세션을 찾을 수 없습니다. ID: " + sessionId);
    }

    public SessionNotFoundException(String meetingCode) {
        super(ErrorCode.SESSION_NOT_FOUND, "공유 세션을 찾을 수 없습니다. 미팅 코드: " + meetingCode);
    }
}
