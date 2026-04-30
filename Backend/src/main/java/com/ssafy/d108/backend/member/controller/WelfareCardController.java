package com.ssafy.d108.backend.member.controller;

import com.ssafy.d108.backend.auth.dto.WelfareCardRequest;
import com.ssafy.d108.backend.auth.dto.WelfareCardResponse;
import com.ssafy.d108.backend.member.service.WelfareCardService;
import com.ssafy.d108.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import com.ssafy.d108.backend.global.exception.BusinessException;
import com.ssafy.d108.backend.global.response.ErrorCode;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

@Tag(name = "복지카드", description = "복지카드 관리 API")
@RestController
@RequestMapping("/welfare")
@RequiredArgsConstructor
public class WelfareCardController {

    private final WelfareCardService welfareCardService;

    private Integer getCurrentUserId() {
        org.springframework.security.core.Authentication authentication = SecurityContextHolder.getContext()
                .getAuthentication();

        if (authentication == null || authentication.getDetails() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }

        return (Integer) authentication.getDetails();
    }

    /**
     * 복지카드 조회
     */
    @Operation(summary = "복지카드 조회", description = "내 복지카드 정보를 조회합니다.")
    @GetMapping
    public ResponseEntity<ApiResponse<WelfareCardResponse>> getWelfareCard() {
        Integer userId = getCurrentUserId();
        WelfareCardResponse response = welfareCardService.getWelfareCard(userId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 복지카드 등록
     */
    @Operation(summary = "복지카드 등록", description = "복지카드를 새로 등록합니다.")
    @PostMapping
    public ResponseEntity<ApiResponse<WelfareCardResponse>> registerWelfareCard(
            @Valid @RequestBody WelfareCardRequest request) {
        Integer userId = getCurrentUserId();
        WelfareCardResponse response = welfareCardService.registerWelfareCard(userId, request);
        return ResponseEntity
                .status(HttpStatus.CREATED)
                .body(ApiResponse.created(response, "복지카드가 등록되었습니다."));
    }

    /**
     * 복지카드 수정
     */
    @Operation(summary = "복지카드 수정", description = "등록된 복지카드를 수정합니다.")
    @PutMapping
    public ResponseEntity<ApiResponse<WelfareCardResponse>> updateWelfareCard(
            @Valid @RequestBody WelfareCardRequest request) {
        Integer userId = getCurrentUserId();
        WelfareCardResponse response = welfareCardService.updateWelfareCard(userId, request);
        return ResponseEntity.ok(ApiResponse.success(response, "복지카드가 수정되었습니다."));
    }

    /**
     * 복지카드 삭제
     */
    @Operation(summary = "복지카드 삭제", description = "내 복지카드를 삭제합니다.")
    @DeleteMapping
    public ResponseEntity<ApiResponse<Void>> deleteWelfareCard() {
        Integer userId = getCurrentUserId();
        welfareCardService.deleteWelfareCard(userId);
        return ResponseEntity.ok(ApiResponse.success(null, "복지카드가 삭제되었습니다."));
    }
}
