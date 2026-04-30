package com.ssafy.d108.backend.member.controller;

import com.ssafy.d108.backend.member.dto.ProfileResponse;
import com.ssafy.d108.backend.member.dto.ProfileUpdateRequest;
import com.ssafy.d108.backend.member.service.ProfileService;
import com.ssafy.d108.backend.global.response.ApiResponse;
import com.ssafy.d108.backend.global.util.SecurityUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/members/profile")
@RequiredArgsConstructor
@Tag(name = "Member Profile", description = "회원 상세 정보(마이페이지) 관련 API")
public class ProfileController {

    private final ProfileService profileService;

    @GetMapping
    @Operation(summary = "내 프로필 조회", description = "로그인한 사용자의 상세 프로필 정보를 조회합니다.")
    public ResponseEntity<ApiResponse<ProfileResponse>> getMyProfile() {
        Integer userId = SecurityUtil.getCurrentUserId();
        return ResponseEntity.ok(ApiResponse.success(profileService.getProfile(userId), "프로필 조회 성공"));
    }

    @PutMapping
    @Operation(summary = "내 프로필 수정", description = "로그인한 사용자의 상세 프로필 정보를 수정합니다.")
    public ResponseEntity<ApiResponse<ProfileResponse>> updateMyProfile(@RequestBody ProfileUpdateRequest request) {
        Integer userId = SecurityUtil.getCurrentUserId();
        return ResponseEntity.ok(ApiResponse.success(profileService.updateProfile(userId, request), "프로필 수정 성공"));
    }
}
