package com.ssafy.d108.backend.wishlist.controller;

import com.ssafy.d108.backend.global.util.SecurityUtil;
import com.ssafy.d108.backend.wishlist.dto.*;
import com.ssafy.d108.backend.wishlist.service.WishlistService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Tag(name = "찜", description = "찜 목록 관리 API")
@RestController
@RequestMapping("/wishlist")
@RequiredArgsConstructor
public class WishlistController {

    private final WishlistService wishlistService;

    /**
     * 찜 추가 (POST /wishlist)
     * Request Header: Authorization (Bearer token)
     * Request Body: WishlistCreateRequestDto
     */
    @Operation(summary = "찜 추가", description = "상품을 찜 목록에 추가합니다.")
    @PostMapping
    public ResponseEntity<WishlistCreateResponse> addWishlistItem(
            @Valid @RequestBody WishlistCreateRequest requestDto) {

        // SecurityUtil을 사용하여 현재 로그인한 유저 ID 추출
        Integer userId = SecurityUtil.getCurrentUserId();

        WishlistCreateResponse response = wishlistService.addWishlistItem(userId, requestDto);
        return ResponseEntity.ok(response);
    }

    /**
     * 찜 목록 조회 (GET /wishlist)
     * Request Header: Authorization (Bearer token)
     */
    @Operation(summary = "찜 목록 조회", description = "사용자의 찜 목록을 조회합니다.")
    @GetMapping
    public ResponseEntity<WishlistResponse> getWishlistItems() {

        // 1. 서버 저장소(SecurityContext)에서 로그인한 유저의 ID를 안전하게 꺼냅니다.
        Integer userId = SecurityUtil.getCurrentUserId();

        // 2. 추출한 ID를 서비스로 넘겨 본인의 목록만 조회합니다.
        WishlistResponse response = wishlistService.getWishlistItems(userId);

        return ResponseEntity.ok(response);
    }

    /**
     * 찜 삭제 (DELETE /wishlist/{wishlistItemId})
     * Request Header: Authorization (Bearer token)
     */
    @Operation(summary = "찜 삭제", description = "찜 목록에서 상품을 삭제합니다.")
    @DeleteMapping("/{wishlistItemId}")
    public ResponseEntity<Void> deleteWishlistItem(
            @PathVariable("wishlistItemId") Integer wishlistItemId) {

        // 서비스에서 존재 여부 확인 후 삭제 수행
        wishlistService.deleteWishlistItem(wishlistItemId);

        // 삭제 성공 시 204 No Content 반환
        return ResponseEntity.noContent().build();
    }
}