package com.ssafy.d108.backend.product.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

/**
 * MCP 서버로부터 받는 상품 정보 요청 DTO
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class ProductRequest {

    /**
     * 상품명
     * 예: "탐사 샘물, 500ml, 40개"
     */
    @JsonProperty("name")
    @NotBlank(message = "상품명은 필수입니다.")
    private String name;

    /**
     * 카테고리 경로 배열
     * 예: ["식품", "사과식초/땅콩버터 외", "생수/음료", "생수", "국산생수"]
     */
    @JsonProperty("category_path")
    @NotEmpty(message = "카테고리 경로는 필수입니다.")
    private List<String> categoryPath;

    /**
     * 쿠팡 상품 고유 번호
     * 예: "7689270513 - 20972233691"
     */
    @JsonProperty("coupang_product_number")
    @NotBlank(message = "쿠팡 상품 번호는 필수입니다.")
    private String coupangProductNumber;
}
