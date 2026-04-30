package com.ssafy.d108.backend.auth.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 복지카드 정보 응답 DTO
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class WelfareCardResponse {

    @JsonProperty("welfare_card_id")
    private Integer welfareCardId;

    @JsonProperty("user_id")
    private Integer userId;

    @JsonProperty("card_company")
    private String cardCompany;

    @JsonProperty("card_number")
    private String cardNumber;

    @JsonProperty("issue_date")
    private LocalDate issueDate;

    @JsonProperty("expiration_date")
    private String expirationDate; // MM/YY 형식

    /**
     * CVC는 보안상 반환하지 않음
     */
    @JsonProperty("has_cvc")
    private boolean hasCvc;

    @JsonProperty("has_welfare_card")
    private boolean hasWelfareCard;

    @JsonProperty("created_at")
    private LocalDateTime createdAt;

    @JsonProperty("updated_at")
    private LocalDateTime updatedAt;
}
