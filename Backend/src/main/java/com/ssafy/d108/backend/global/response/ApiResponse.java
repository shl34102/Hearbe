package com.ssafy.d108.backend.global.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 표준 API 응답 래퍼 클래스
 * 모든 API 응답은 이 형식을 따라 일관성을 유지합니다.
 * 
 * @param <T> 응답 데이터의 타입
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {

    private Integer code; // 응답 코드
    private String message; // 응답 메시지
    private T data; // 응답 데이터

    /**
     * 성공 응답 생성 (데이터 포함)
     */
    public static <T> ApiResponse<T> success(T data) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.SUCCESS.getCode())
                .message(ErrorCode.SUCCESS.getMessage())
                .data(data)
                .build();
    }

    /**
     * 성공 응답 생성 (커스텀 메시지 포함)
     */
    public static <T> ApiResponse<T> success(T data, String message) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.SUCCESS.getCode())
                .message(message)
                .data(data)
                .build();
    }

    /**
     * 생성 성공 응답
     */
    public static <T> ApiResponse<T> created(T data) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.CREATED.getCode())
                .message(ErrorCode.CREATED.getMessage())
                .data(data)
                .build();
    }

    /**
     * 생성 성공 응답 (커스텀 메시지 포함)
     */
    public static <T> ApiResponse<T> created(T data, String message) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.CREATED.getCode())
                .message(message)
                .data(data)
                .build();
    }

    /**
     * 실패 응답 생성 (ErrorCode 사용)
     */
    public static <T> ApiResponse<T> failure(ErrorCode errorCode) {
        return ApiResponse.<T>builder()
                .code(errorCode.getCode())
                .message(errorCode.getMessage())
                .data(null)
                .build();
    }

    /**
     * 실패 응답 생성 (커스텀 메시지 포함)
     */
    public static <T> ApiResponse<T> failure(ErrorCode errorCode, String message) {
        return ApiResponse.<T>builder()
                .code(errorCode.getCode())
                .message(message)
                .data(null)
                .build();
    }

    /**
     * 실패 응답 생성 (코드와 메시지 직접 지정)
     */
    public static <T> ApiResponse<T> failure(Integer code, String message) {
        return ApiResponse.<T>builder()
                .code(code)
                .message(message)
                .data(null)
                .build();
    }

    /**
     * 커스텀 응답 생성 (모든 필드 지정)
     */
    public static <T> ApiResponse<T> of(Integer code, String message, T data) {
        return ApiResponse.<T>builder()
                .code(code)
                .message(message)
                .data(data)
                .build();
    }

    /**
     * ErrorCode로부터 응답 생성
     */
    public static <T> ApiResponse<T> of(ErrorCode errorCode) {
        return ApiResponse.<T>builder()
                .code(errorCode.getCode())
                .message(errorCode.getMessage())
                .data(null)
                .build();
    }

    /**
     * ErrorCode와 데이터로 응답 생성
     */
    public static <T> ApiResponse<T> of(ErrorCode errorCode, T data) {
        return ApiResponse.<T>builder()
                .code(errorCode.getCode())
                .message(errorCode.getMessage())
                .data(data)
                .build();
    }
}
