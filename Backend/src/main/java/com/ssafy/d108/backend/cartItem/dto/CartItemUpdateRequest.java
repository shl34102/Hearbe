package com.ssafy.d108.backend.cartItem.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class CartItemUpdateRequest {

    @JsonProperty("quantity")
    @Min(value = 1, message = "수량은 최소 1개 이상이어야 합니다.")
    private int quantity;

}