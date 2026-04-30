package com.ssafy.d108.backend.auth.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.ssafy.d108.backend.entity.enums.UserType;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 회원가입 요청 DTO
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class SignupRequest {

    @JsonProperty("username")
    @NotBlank(message = "아이디는 필수입니다.")
    @Size(min = 4, max = 30, message = "아이디는 4~30자 사이여야 합니다.")
    private String username;

    private String password;

    @JsonProperty("password_check")
    private String passwordCheck;

    @NotBlank(message = "이름은 필수입니다.")
    @Size(max = 15, message = "이름은 15자 이하여야 합니다.")
    private String name;

    private String email;

    @JsonProperty("phone_number")
    @Pattern(regexp = "^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$")
    private String phoneNumber;

    @JsonProperty("user_type")
    @NotNull(message = "사용자 타입은 필수입니다.")
    private UserType userType;

    @JsonProperty("simple_password")
    @Pattern(regexp = "^[0-9]{6}$", message = "간편 비밀번호는 6자리 숫자여야 합니다.")
    private String simplePassword;

    /**
     * 복지카드 정보 (BLIND 타입일 경우 필수)
     */
    @JsonProperty("welfare_card")
    @Valid
    private WelfareCardRequest welfareCard;
}
