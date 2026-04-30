package com.ssafy.d108.backend.auth.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class CheckIdRequest {
    @NotBlank(message = "아이디는 필수입니다.")
    private String username;
}
