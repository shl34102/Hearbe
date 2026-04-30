package com.ssafy.d108.backend.order.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.ssafy.d108.backend.entity.Order;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class OrderResponse {

    @JsonProperty("order_id")
    private Integer orderId;

    @JsonProperty("pay_status")
    private String payStatus; // "PAID" hardcoded or from entity

    @JsonProperty("ordered_at")
    private LocalDateTime orderedAt;

    @JsonProperty("order_url")
    private String orderUrl;

    @JsonProperty("items")
    private List<OrderItemResponse> items;

    public static OrderResponse of(Order order, List<OrderItemResponse> items) {
        return new OrderResponse(
                order.getId(),
                "PAID", // Default for now
                order.getCreatedAt(),
                order.getOrderDetailUrl(),
                items);
    }
}
