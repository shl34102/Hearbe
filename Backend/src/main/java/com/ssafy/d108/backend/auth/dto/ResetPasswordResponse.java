package com.ssafy.d108.backend.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 비밀번호 재설정 응답 DTO
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class ResetPasswordResponse {

    private String result;

    public static ResetPasswordResponse success() {
        return new ResetPasswordResponse("success");
    }

    public static ResetPasswordResponse failure() {
        return new ResetPasswordResponse("false");
    }
}
