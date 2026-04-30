package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 플랫폼 동기화 실패 예외
 * 외부 쇼핑몰과의 상품 정보 동기화가 실패했을 때 발생
 */
public class PlatformSyncException extends BusinessException {

    public PlatformSyncException() {
        super(ErrorCode.PLATFORM_SYNC_FAILED);
    }

    public PlatformSyncException(String platformName) {
        super(ErrorCode.PLATFORM_SYNC_FAILED, platformName + " 연동에 실패했습니다.");
    }

    public PlatformSyncException(String platformName, Throwable cause) {
        super(ErrorCode.PLATFORM_SYNC_FAILED, platformName + " 연동에 실패했습니다.", cause);
    }
}
