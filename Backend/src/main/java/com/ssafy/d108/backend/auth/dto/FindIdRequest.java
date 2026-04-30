package com.ssafy.d108.backend.auth.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 아이디 찾기 요청 DTO (A형 - 복지카드 인증)
 * - 구조 변경: UserType 및 복지카드 객체 중첩 구조 사용
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class FindIdRequest {

    @JsonProperty("welfare_card")
    @Valid
    @NotNull(message = "복지카드 정보는 필수입니다.")
    private WelfareCardRequest welfareCard;
}
