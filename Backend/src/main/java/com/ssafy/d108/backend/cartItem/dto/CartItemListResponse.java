package com.ssafy.d108.backend.cartItem.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
@NoArgsConstructor
public class CartItemListResponse {

    @JsonProperty("cart_items")
    private List<CartItemDetail> cartItems;

    @JsonProperty("total_count")
    private int totalCount;

    @JsonProperty("total_price")
    private int totalPrice;

    @Getter
    @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CartItemDetail {

        @JsonProperty("cart_item_id")
        private Long cartItemId;

        @JsonProperty("platform_id")
        private Long platformId;

        @JsonProperty("name")
        private String name;

        @JsonProperty("price")
        private int price;

        @JsonProperty("img_url")
        private String imgUrl;

        @JsonProperty("url")
        private String url;

        @JsonProperty("quantity")
        private int quantity;

        @JsonProperty("created_at")
        private String createdAt;
    }
}