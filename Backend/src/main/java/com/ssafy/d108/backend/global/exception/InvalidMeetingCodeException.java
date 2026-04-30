package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 유효하지 않은 미팅 코드 예외
 * 잘못된 형식이거나 존재하지 않는 미팅 코드로 세션에 참가하려 할 때 발생
 */
public class InvalidMeetingCodeException extends BusinessException {

    public InvalidMeetingCodeException() {
        super(ErrorCode.INVALID_MEETING_CODE);
    }

    public InvalidMeetingCodeException(String meetingCode) {
        super(ErrorCode.INVALID_MEETING_CODE, "유효하지 않은 미팅 코드입니다: " + meetingCode);
    }
}
