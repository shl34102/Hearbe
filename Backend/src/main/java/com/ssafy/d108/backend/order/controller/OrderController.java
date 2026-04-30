package com.ssafy.d108.backend.order.controller;

import com.ssafy.d108.backend.global.response.ApiResponse;
import com.ssafy.d108.backend.global.util.SecurityUtil;
import com.ssafy.d108.backend.order.dto.OrderCreateRequest;
import com.ssafy.d108.backend.order.dto.OrderListResponse;
import com.ssafy.d108.backend.order.dto.OrderResponse;
import com.ssafy.d108.backend.order.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Tag(name = "주문", description = "주문 및 결제 관련 API")
@RestController
@RequestMapping("/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    @Operation(summary = "주문 생성", description = "단일 상품을 주문합니다.")
    @PostMapping
    public ResponseEntity<ApiResponse<OrderResponse>> createOrder(@Valid @RequestBody OrderCreateRequest request) {
        Integer userId = SecurityUtil.getCurrentUserId();
        OrderResponse response = orderService.createOrder(userId, request);
        return ResponseEntity
                .status(HttpStatus.CREATED)
                .body(ApiResponse.created(response, "주문이 완료되었습니다."));
    }

    @Operation(summary = "내 주문 내역 조회", description = "나의 전체 주문 내역을 조회합니다.")
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<OrderListResponse>> getMyOrders() {
        Integer userId = SecurityUtil.getCurrentUserId();
        OrderListResponse response = orderService.getMyOrders(userId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
