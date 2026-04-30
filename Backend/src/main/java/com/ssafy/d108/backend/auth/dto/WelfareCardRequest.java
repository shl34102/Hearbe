package com.ssafy.d108.backend.auth.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;

/**
 * 복지카드 등록 요청 DTO
 * AI 서버의 OCR 결과를 받아서 저장
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class WelfareCardRequest {

    @JsonProperty("card_company")
    @NotNull(message = "카드사는 필수입니다.")
    private String cardCompany;

    @JsonProperty("card_number")
    @NotNull(message = "복지카드 번호는 필수입니다.")
    private String cardNumber;

    @JsonProperty("issue_date")
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate issueDate;

    @JsonProperty("expiration_date")
    @NotNull(message = "만료일은 필수입니다.")
    @Pattern(regexp = "^(0[1-9]|1[0-2])/[0-9]{2}$", message = "유효기간은 MM/YY 형식이어야 합니다. (예: 12/26)")
    private String expirationDate; // MM/YY 형식

    @JsonProperty("cvc")
    @NotNull(message = "CVC는 필수입니다.")
    @Pattern(regexp = "^[0-9]{3,5}$", message = "CVC는 3~5자리 숫자여야 합니다.")
    private String cvc;
}
