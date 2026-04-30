package com.ssafy.d108.backend.wishlist.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.util.List;

@Getter
@Setter
@NoArgsConstructor
public class WishlistResponse {

    @JsonProperty("total_count")
    private int totalCount;

    @JsonProperty("total_price")
    private long totalPrice;

    @JsonProperty("items")
    private List<WishlistItemDetail> items;

    @Getter
    @Setter
    @NoArgsConstructor
    public static class WishlistItemDetail {

        @JsonProperty("wishlist_item_id")
        private Integer wishlistItemId;

        @JsonProperty("product_name")
        private String productName;

        @JsonProperty("product_url")
        private String productUrl;

        @JsonProperty("platform_name")
        private String platformName;

        @JsonProperty("created_at")
        private String createdAt;

        @JsonProperty("img_url")
        private String imgUrl;

        @JsonProperty("price")
        private long price;

        @JsonProperty("liked")
        private Boolean liked;
    }
}