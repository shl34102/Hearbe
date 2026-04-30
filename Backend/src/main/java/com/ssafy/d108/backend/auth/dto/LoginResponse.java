package com.ssafy.d108.backend.auth.dto;

import com.ssafy.d108.backend.entity.enums.UserType;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 로그인 응답 DTO
 */
@Getter
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponse {
    private Integer id;
    private String name;
    private UserType userType;
    private String accessToken;
    // refreshToken은 HttpOnly 쿠키로 전달되므로 응답 본문에서 제거
    private String message;
}
