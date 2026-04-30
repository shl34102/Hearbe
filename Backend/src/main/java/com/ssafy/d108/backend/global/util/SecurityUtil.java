package com.ssafy.d108.backend.global.util;

import com.ssafy.d108.backend.global.exception.BusinessException;
import com.ssafy.d108.backend.global.response.ErrorCode;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

public class SecurityUtil {
    public static Integer getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();

        if (authentication == null || authentication.getDetails() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }

        // 추가된 안전 장치: 타입이 Integer인지 확인
        Object details = authentication.getDetails();
        if (!(details instanceof Integer)) {
            // 이 오류가 뜨면 로그인 담당 팀원에게 "details에 Integer가 아니라 WebAuthenticationDetails가 들어와요"라고
            // 말해야 합니다.
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }

        return (Integer) details;
        // return 1;
    }
}