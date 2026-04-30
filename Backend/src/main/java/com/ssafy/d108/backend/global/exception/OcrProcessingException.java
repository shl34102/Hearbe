package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * OCR 처리 실패 예외
 * 이미지 인식 중 오류가 발생했을 때 사용
 */
public class OcrProcessingException extends BusinessException {

    public OcrProcessingException() {
        super(ErrorCode.OCR_PROCESSING_FAILED);
    }

    public OcrProcessingException(String message) {
        super(ErrorCode.OCR_PROCESSING_FAILED, message);
    }

    public OcrProcessingException(String message, Throwable cause) {
        super(ErrorCode.OCR_PROCESSING_FAILED, message, cause);
    }
}
