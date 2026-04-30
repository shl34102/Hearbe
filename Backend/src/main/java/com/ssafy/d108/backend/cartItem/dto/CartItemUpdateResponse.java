package com.ssafy.d108.backend.cartItem.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class CartItemUpdateResponse {

    @JsonProperty("cart_item_id")
    private Long cartItemId;

    @JsonProperty("message")
    private String message;
}