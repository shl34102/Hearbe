package com.ssafy.d108.backend.wishlist.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class WishlistCreateResponse {

    @JsonProperty("wishlist_item_id")
    private Integer wishlistItemId;

    @JsonProperty("created_at")
    private String createdAt;

}