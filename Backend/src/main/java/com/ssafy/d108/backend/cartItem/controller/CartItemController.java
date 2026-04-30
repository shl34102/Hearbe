package com.ssafy.d108.backend.cartItem.controller;

import com.ssafy.d108.backend.cartItem.dto.*;
import com.ssafy.d108.backend.cartItem.service.CartItemService;
import com.ssafy.d108.backend.global.util.SecurityUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@Tag(name = "장바구니", description = "장바구니 관리 API")
@RestController
@RequestMapping("/cart")
@RequiredArgsConstructor
public class CartItemController {

    private final CartItemService cartItemService;

    /**
     * 장바구니 담기
     */
    @PostMapping
    public ResponseEntity<CartItemCreateResponse> addCartItem(
            @Valid @RequestBody CartItemRequest requestDto) {

        // SecurityUtil에서 추출한 ID를 사용하여 안전하게 저장
        return ResponseEntity.ok(cartItemService.addCartItem(SecurityUtil.getCurrentUserId(), requestDto));
    }

    /**
     * 장바구니 목록 조회
     */
    @GetMapping
    public ResponseEntity<CartItemListResponse> getCartItems() {

        // 경로 변수(@PathVariable) 대신 SecurityUtil을 사용하여
        // "로그인한 유저 본인"의 ID를 꺼내옵니다.
        Integer userId = SecurityUtil.getCurrentUserId();

        // 본인의 ID로만 조회하므로 다른 사람의 정보를 볼 수 없어 안전합니다.
        CartItemListResponse response = cartItemService.getCartItems(userId);

        return ResponseEntity.ok(response);
    }

    /**
     * 장바구니 수량 수정
     */
    @PatchMapping("/{cart_item_id}")
    public ResponseEntity<CartItemUpdateResponse> updateQuantity(
            @PathVariable("cart_item_id") Integer cartItemId,
            @Valid @RequestBody CartItemUpdateRequest requestDto) {

        return ResponseEntity.ok(cartItemService.updateQuantity(cartItemId, requestDto));
    }

    /**
     * 장바구니 삭제
     */
    @DeleteMapping("/{cart_item_id}")
    public ResponseEntity<Map<String, String>> deleteCartItem(
            @PathVariable("cart_item_id") Integer cartItemId) {

        cartItemService.deleteCartItem(cartItemId);

        Map<String, String> response = new HashMap<>();
        response.put("message", "상품이 성공적으로 삭제되었습니다.");

        return ResponseEntity.ok(response);
    }
}