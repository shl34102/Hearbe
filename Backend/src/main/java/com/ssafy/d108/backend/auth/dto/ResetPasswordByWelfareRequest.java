package com.ssafy.d108.backend.auth.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 비밀번호 재설정 요청 DTO (A형 - 복지카드 인증)
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class ResetPasswordByWelfareRequest {

    @JsonProperty("welfare_card")
    @NotNull(message = "복지카드 정보는 필수입니다.")
    @Valid
    private WelfareCardRequest welfareCard;

    @JsonProperty("new_password")
    @NotBlank(message = "새 비밀번호는 필수입니다.")
    @Pattern(regexp = "^[0-9]{6}$", message = "비밀번호는 숫자 6자리 여야 합니다.")
    private String newPassword;
}
