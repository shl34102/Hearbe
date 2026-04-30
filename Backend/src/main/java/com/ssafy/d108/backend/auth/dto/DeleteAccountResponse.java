package com.ssafy.d108.backend.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 회원탈퇴 응답 DTO
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class DeleteAccountResponse {

    private Integer userId;
    private String message;

    public static DeleteAccountResponse of(Integer userId) {
        return new DeleteAccountResponse(userId, "회원탈퇴가 완료되었습니다.");
    }
}
