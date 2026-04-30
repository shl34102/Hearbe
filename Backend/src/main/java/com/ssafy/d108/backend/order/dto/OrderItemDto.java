package com.ssafy.d108.backend.order.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

/**
 * 주문 생성 시 개별 아이템 정보
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class OrderItemDto {

    @JsonProperty("name")
    @NotBlank(message = "상품명은 필수입니다.")
    private String name;

    @JsonProperty("price")
    @NotNull(message = "가격은 필수입니다.")
    @Min(value = 0, message = "가격은 0 이상이어야 합니다.")
    private Long price;

    @JsonProperty("quantity")
    @NotNull(message = "수량은 필수입니다.")
    @Min(value = 1, message = "수량은 1 이상이어야 합니다.")
    private Integer quantity;

    @JsonProperty("url")
    private String url;

    @JsonProperty("img_url")
    private String imgUrl;

    @JsonProperty("deliver_url")
    private String deliverUrl;

    /**
     * 쿠팡 상품 고유 번호 (선택 사항)
     * 예: "7689270513 - 20972233691"
     */
    @JsonProperty("coupang_product_number")
    private String coupangProductNumber;

    /**
     * 카테고리 경로 배열 (선택 사항)
     * 예: ["식품", "사과식초/땅콩버터 외", "생수/음료", "생수", "국산생수"]
     */
    @JsonProperty("category_path")
    private List<String> categoryPath;
}
