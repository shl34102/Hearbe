package com.ssafy.d108.backend.cartItem.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.ToString;

@Getter
@Setter
@NoArgsConstructor
@ToString
public class CartItemRequest {

    @JsonProperty("platform_id")
    @NotNull(message = "플랫폼 ID는 필수입니다.")
    private Long platformId;

    @NotBlank(message = "상품명은 비어있을 수 없습니다.")
    private String name;

    @JsonProperty("product_url")
    @NotBlank(message = "상품 URL은 필수입니다.")
    private String url;

    @JsonProperty("img_url")
    @NotBlank(message = "이미지 URL은 필수입니다.")
    private String imgUrl;

    @Min(value = 0, message = "가격은 0원 이상이어야 합니다.")
    private int price;
}