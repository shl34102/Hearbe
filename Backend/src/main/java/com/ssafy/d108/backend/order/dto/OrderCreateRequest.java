package com.ssafy.d108.backend.order.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

/**
 * 주문 생성 요청 DTO
 * 여러 아이템을 한 번에 주문할 수 있음
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class OrderCreateRequest {

    @JsonProperty("platform_id")
    @NotNull(message = "플랫폼 ID는 필수입니다.")
    private Long platformId;

    @JsonProperty("order_url")
    private String orderUrl;

    @Valid
    @NotEmpty(message = "주문 아이템은 최소 1개 이상이어야 합니다.")
    private List<OrderItemDto> items;
}
