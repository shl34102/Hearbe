package com.ssafy.d108.backend.global.exceptionhandler;

import com.ssafy.d108.backend.global.exception.BusinessException;
import com.ssafy.d108.backend.global.response.ApiResponse;
import com.ssafy.d108.backend.global.response.ErrorCode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.RedisSystemException;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.NoHandlerFoundException;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * 전역 예외 처리를 담당하는 핸들러
 * 
 * - 중앙집중식 예외 처리를 통해 일관된 에러 응답 제공
 * - 시각장애인 사용자를 위한 명확한 에러 메시지 제공
 * - 모든 예외를 ApiResponse 형식으로 변환하여 반환
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

        /**
         * 비즈니스 로직 예외 처리
         * 모든 커스텀 예외(BusinessException 및 하위 클래스)를 처리
         */
        @ExceptionHandler(BusinessException.class)
        public ResponseEntity<ApiResponse<Void>> handleBusinessException(BusinessException e) {
                log.warn("Business exception occurred: {} - {}", e.getErrorCode(), e.getMessage());

                ErrorCode errorCode = e.getErrorCode();
                ApiResponse<Void> response = ApiResponse.failure(errorCode, e.getMessage());

                return ResponseEntity
                                .status(errorCode.getStatus())
                                .body(response);
        }

        /**
         * Validation 예외 처리
         * 
         * @Valid 어노테이션을 사용한 입력값 검증 실패 시 발생
         */
        @ExceptionHandler(MethodArgumentNotValidException.class)
        public ResponseEntity<ApiResponse<Map<String, String>>> handleValidationException(
                        MethodArgumentNotValidException e) {

                log.warn("Validation error occurred");

                Map<String, String> errors = new HashMap<>();
                e.getBindingResult().getAllErrors().forEach(error -> {
                        String fieldName = ((FieldError) error).getField();
                        String errorMessage = error.getDefaultMessage();
                        errors.put(fieldName, errorMessage);
                });

                ApiResponse<Map<String, String>> response = ApiResponse.of(
                                ErrorCode.VALIDATION_ERROR.getCode(),
                                ErrorCode.VALIDATION_ERROR.getMessage(),
                                errors);

                return ResponseEntity
                                .status(ErrorCode.VALIDATION_ERROR.getStatus())
                                .body(response);
        }

        /**
         * IllegalArgumentException 처리
         * 잘못된 인자가 전달되었을 때 발생
         */
        @ExceptionHandler(IllegalArgumentException.class)
        public ResponseEntity<ApiResponse<Void>> handleIllegalArgumentException(IllegalArgumentException e) {
                log.warn("Illegal argument: {}", e.getMessage());

                ApiResponse<Void> response = ApiResponse.failure(
                                ErrorCode.INVALID_INPUT,
                                e.getMessage());

                return ResponseEntity
                                .status(ErrorCode.INVALID_INPUT.getStatus())
                                .body(response);
        }

        /**
         * 데이터베이스 관련 예외 처리
         */
        @ExceptionHandler(DataAccessException.class)
        public ResponseEntity<ApiResponse<Void>> handleDataAccessException(DataAccessException e) {
                log.error("Database error occurred", e);

                ApiResponse<Void> response = ApiResponse.failure(ErrorCode.DATABASE_ERROR);

                return ResponseEntity
                                .status(ErrorCode.DATABASE_ERROR.getStatus())
                                .body(response);
        }

        /**
         * Redis 연결 예외 처리
         */
        @ExceptionHandler({ RedisConnectionFailureException.class, RedisSystemException.class })
        public ResponseEntity<ApiResponse<Void>> handleRedisException(Exception e) {
                log.error("Redis connection error occurred", e);

                ApiResponse<Void> response = ApiResponse.failure(ErrorCode.REDIS_CONNECTION_ERROR);

                return ResponseEntity
                                .status(ErrorCode.REDIS_CONNECTION_ERROR.getStatus())
                                .body(response);
        }

        /**
         * 파일 업로드 크기 초과 예외 처리
         */
        @ExceptionHandler(MaxUploadSizeExceededException.class)
        public ResponseEntity<ApiResponse<Void>> handleMaxUploadSizeException(
                        MaxUploadSizeExceededException e) {

                log.warn("File size exceeded: {}", e.getMessage());

                ApiResponse<Void> response = ApiResponse.failure(
                                ErrorCode.INVALID_INPUT,
                                "파일 크기가 너무 큽니다. 10MB 이하의 파일을 업로드해주세요.");

                return ResponseEntity
                                .status(ErrorCode.INVALID_INPUT.getStatus())
                                .body(response);
        }

        /**
         * 파일을 찾을 수 없는 경우 예외 처리
         */
        @ExceptionHandler(FileNotFoundException.class)
        public ResponseEntity<ApiResponse<Void>> handleFileNotFoundException(FileNotFoundException e) {
                log.warn("File not found: {}", e.getMessage());

                ApiResponse<Void> response = ApiResponse.failure(
                                ErrorCode.INVALID_INPUT.getCode(),
                                "파일을 찾을 수 없습니다.");

                return ResponseEntity
                                .status(ErrorCode.INVALID_INPUT.getStatus())
                                .body(response);
        }

        /**
         * 파일 입출력 예외 처리
         */
        @ExceptionHandler(IOException.class)
        public ResponseEntity<ApiResponse<Void>> handleIOException(IOException e) {
                log.error("IO error occurred", e);

                ApiResponse<Void> response = ApiResponse.failure(
                                ErrorCode.INTERNAL_SERVER_ERROR,
                                "파일 처리 중 오류가 발생했습니다.");

                return ResponseEntity
                                .status(ErrorCode.INTERNAL_SERVER_ERROR.getStatus())
                                .body(response);
        }

        /**
         * PathVariable 변환 실패 예외 처리 (잘못된 경로 매개변수)
         */
        @ExceptionHandler(MethodArgumentTypeMismatchException.class)
        public ResponseEntity<ApiResponse<Void>> handleMethodArgumentTypeMismatchException(
                        MethodArgumentTypeMismatchException e) {

                log.warn("Type mismatch for parameter '{}': {}", e.getName(), e.getMessage());

                ApiResponse<Void> response = ApiResponse.failure(
                                ErrorCode.INVALID_INPUT,
                                "잘못된 요청입니다. 입력값을 확인해주세요.");

                return ResponseEntity
                                .status(ErrorCode.INVALID_INPUT.getStatus())
                                .body(response);
        }

        /**
         * NoHandlerFoundException 처리 (매핑되지 않은 URL)
         */
        @ExceptionHandler(NoHandlerFoundException.class)
        public ResponseEntity<ApiResponse<Void>> handleNoHandlerFoundException(
                        NoHandlerFoundException e) {

                log.warn("No handler found for {} {}", e.getHttpMethod(), e.getRequestURL());

                ApiResponse<Void> response = ApiResponse.failure(
                                ErrorCode.INVALID_INPUT.getCode(),
                                "요청한 페이지를 찾을 수 없습니다.");

                return ResponseEntity
                                .status(ErrorCode.INVALID_INPUT.getStatus())
                                .body(response);
        }

        /**
         * RuntimeException 처리
         * 예상치 못한 런타임 예외 처리
         */
        @ExceptionHandler(RuntimeException.class)
        public ResponseEntity<ApiResponse<Void>> handleRuntimeException(RuntimeException e) {
                log.error("Unexpected runtime error occurred", e);

                ApiResponse<Void> response = ApiResponse.failure(ErrorCode.INTERNAL_SERVER_ERROR);

                return ResponseEntity
                                .status(ErrorCode.INTERNAL_SERVER_ERROR.getStatus())
                                .body(response);
        }

        /**
         * 일반적인 예외 처리 (마지막 fallback)
         * 위에서 처리되지 않은 모든 예외를 처리
         */
        @ExceptionHandler(Exception.class)
        public ResponseEntity<ApiResponse<Void>> handleGenericException(Exception e) {
                log.error("Unexpected error occurred", e);

                ApiResponse<Void> response = ApiResponse.failure(
                                ErrorCode.INTERNAL_SERVER_ERROR,
                                "예기치 않은 오류가 발생했습니다. 관리자에게 문의해주세요.");

                return ResponseEntity
                                .status(ErrorCode.INTERNAL_SERVER_ERROR.getStatus())
                                .body(response);
        }
}
