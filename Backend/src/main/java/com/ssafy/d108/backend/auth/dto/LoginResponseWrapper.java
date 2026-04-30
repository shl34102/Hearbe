package com.ssafy.d108.backend.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 로그인 응답 래퍼 (refreshToken 포함)
 * Controller에서 refreshToken을 HttpOnly 쿠키로 설정하기 위해 사용
 */
@Getter
@AllArgsConstructor
public class LoginResponseWrapper {
    private LoginResponse loginResponse;
    private String refreshToken;
}
