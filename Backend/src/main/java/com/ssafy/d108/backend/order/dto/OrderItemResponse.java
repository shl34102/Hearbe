package com.ssafy.d108.backend.order.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.ssafy.d108.backend.entity.OrderItem;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class OrderItemResponse {

    @JsonProperty("name")
    private String name;

    @JsonProperty("price")
    private Long price;

    @JsonProperty("quantity")
    private Integer quantity;

    @JsonProperty("url")
    private String url;

    @JsonProperty("img_url")
    private String imgUrl;

    @JsonProperty("deliver_url")
    private String deliverUrl;

    public static OrderItemResponse from(OrderItem item) {
        return new OrderItemResponse(
                item.getName(),
                item.getPrice(),
                item.getQuantity(),
                item.getUrl(),
                item.getImgUrl(),
                item.getDeliverUrl());
    }
}
