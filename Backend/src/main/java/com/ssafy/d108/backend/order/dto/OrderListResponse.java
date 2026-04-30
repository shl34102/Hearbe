package com.ssafy.d108.backend.order.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.ssafy.d108.backend.entity.Order;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

import com.ssafy.d108.backend.product.dto.RecommendedProductDto;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class OrderListResponse {

    @JsonProperty("orders")
    private List<OrderDetailDto> orders;

    @JsonProperty("recommended_products")
    private List<RecommendedProductDto> recommendedProducts;

    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class OrderDetailDto {
        @JsonProperty("order_id")
        private Integer orderId;

        @JsonProperty("ordered_at")
        private String orderedAt;

        @JsonProperty("order_url")
        private String orderUrl;

        @JsonProperty("platform_id")
        private Long platformId;

        @JsonProperty("items")
        private List<OrderItemResponse> items;

        public static OrderDetailDto from(Order order, List<OrderItemResponse> items, Long platformId) {
            String formattedDate = order.getCreatedAt().toLocalDate().toString();

            return new OrderDetailDto(
                    order.getId(),
                    formattedDate,
                    order.getOrderDetailUrl(),
                    platformId,
                    items);
        }
    }
}
