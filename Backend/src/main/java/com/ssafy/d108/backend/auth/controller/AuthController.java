package com.ssafy.d108.backend.auth.controller;

import com.ssafy.d108.backend.auth.dto.DeleteAccountRequest;
import com.ssafy.d108.backend.auth.dto.DeleteAccountResponse;
import com.ssafy.d108.backend.auth.dto.FindIdRequest;
import com.ssafy.d108.backend.auth.dto.FindIdByEmailRequest;
import com.ssafy.d108.backend.auth.dto.FindIdResponse;
import com.ssafy.d108.backend.auth.dto.CheckIdRequest;
import com.ssafy.d108.backend.auth.dto.LoginRequest;
import com.ssafy.d108.backend.auth.dto.LoginResponse;
import com.ssafy.d108.backend.auth.dto.LoginResponseWrapper;
import com.ssafy.d108.backend.auth.dto.RefreshTokenRequest;
import com.ssafy.d108.backend.auth.dto.RefreshTokenResponse;
import com.ssafy.d108.backend.auth.dto.ResetPasswordByWelfareRequest;
import com.ssafy.d108.backend.auth.dto.ResetPasswordRequest;
import com.ssafy.d108.backend.auth.dto.ResetPasswordResponse;
import com.ssafy.d108.backend.global.util.SecurityUtil;
import com.ssafy.d108.backend.auth.dto.SignupRequest;
import com.ssafy.d108.backend.auth.service.AuthService;
import com.ssafy.d108.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 인증 컨트롤러 (B/C형)
 */
@Tag(name = "인증", description = "회원가입 및 로그인 API")
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    /**
     * 회원가입
     */
    @Operation(summary = "회원가입", description = "B/C형 사용자 회원가입 (복지카드 불필요)")
    @PostMapping("/regist")
    public ResponseEntity<ApiResponse<Integer>> signup(@Valid @RequestBody SignupRequest request) {
        Integer userId = authService.signup(request);
        return ResponseEntity
                .status(HttpStatus.CREATED)
                .body(ApiResponse.created(userId, "회원가입 완료"));
    }

    /**
     * 로그인
     */
    @Operation(summary = "로그인", description = "아이디/비밀번호로 로그인")
    @PostMapping("/login")
    public ResponseEntity<ApiResponse<LoginResponse>> login(
            @Valid @RequestBody LoginRequest request,
            jakarta.servlet.http.HttpServletResponse response) {

        LoginResponseWrapper wrapper = authService.login(request);

        // refreshToken을 HttpOnly 쿠키로 설정 (XSS 공격 방어)
        jakarta.servlet.http.Cookie cookie = new jakarta.servlet.http.Cookie("refreshToken", wrapper.getRefreshToken());
        cookie.setHttpOnly(true); // JavaScript 접근 차단
        cookie.setSecure(true); // HTTPS only (운영 환경)
        cookie.setPath("/");
        cookie.setMaxAge(14 * 24 * 60 * 60); // 14일
        cookie.setAttribute("SameSite", "Strict"); // CSRF 방어

        response.addCookie(cookie);

        return ResponseEntity.ok(ApiResponse.success(wrapper.getLoginResponse()));
    }

    /**
     * 토큰 재발급
     */
    @Operation(summary = "토큰 재발급", description = "Refresh Token으로 Access Token 재발급")
    @PostMapping("/refresh")
    public ResponseEntity<ApiResponse<RefreshTokenResponse>> refresh(
            @org.springframework.web.bind.annotation.CookieValue(value = "refreshToken", required = false) String refreshToken,
            jakarta.servlet.http.HttpServletResponse response) {

        if (refreshToken == null || refreshToken.isEmpty()) {
            throw new com.ssafy.d108.backend.global.exception.UnauthorizedException("인증 정보가 없습니다.");
        }

        RefreshTokenResponse tokenResponse = authService.refreshToken(new RefreshTokenRequest(refreshToken));

        // 새 refreshToken을 HttpOnly 쿠키로 설정
        jakarta.servlet.http.Cookie cookie = new jakarta.servlet.http.Cookie("refreshToken",
                tokenResponse.getRefreshToken());
        cookie.setHttpOnly(true);
        cookie.setSecure(true);
        cookie.setPath("/");
        cookie.setMaxAge(14 * 24 * 60 * 60); // 14일
        cookie.setAttribute("SameSite", "Strict");

        response.addCookie(cookie);

        return ResponseEntity.ok(ApiResponse.success(tokenResponse));
    }

    /**
     * 아이디 찾기 (A형 - 복지카드 인증)
     */
    @Operation(summary = "아이디 찾기", description = "복지카드 정보로 아이디 찾기 (A형 전용)")
    @PostMapping("/findId")
    public ResponseEntity<ApiResponse<FindIdResponse>> findId(@Valid @RequestBody FindIdRequest request) {
        FindIdResponse response = authService.findId(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 아이디 중복 확인
     */
    @Operation(summary = "아이디 중복 확인", description = "아이디 중복 여부를 확인합니다. true: 중복, false: 사용 가능")
    @PostMapping("/checkId")
    public ResponseEntity<ApiResponse<Boolean>> checkId(@Valid @RequestBody CheckIdRequest request) {
        boolean isDuplicate = authService.checkIdDuplicate(request.getUsername());
        return ResponseEntity.ok(ApiResponse.success(isDuplicate, isDuplicate ? "이미 사용 중인 아이디입니다." : "사용 가능한 아이디입니다."));
    }

    /**
     * 로그아웃
     */
    @Operation(summary = "로그아웃", description = "로그아웃 처리 (추후 토큰 만료 로직 포함)")
    @PostMapping("/logout")
    public ResponseEntity<ApiResponse<Void>> logout() {
        return ResponseEntity.ok(ApiResponse.success(null, "로그아웃 되었습니다."));
    }

    /**
     * 아이디 찾기 (C형 - 이메일 인증)
     */
    @Operation(summary = "아이디 찾기 (이메일)", description = "이름과 이메일로 아이디 찾기 (C형 전용)")
    @PostMapping("/findIdByEmail")
    public ResponseEntity<ApiResponse<FindIdResponse>> findIdByEmail(@Valid @RequestBody FindIdByEmailRequest request) {
        FindIdResponse response = authService.findIdByEmail(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 비밀번호 재설정 (C형 - 이메일 인증)
     */
    @Operation(summary = "비밀번호 재설정", description = "이메일 인증 후 비밀번호 재설정 (C형 전용)")
    @PostMapping("/resetPassword")
    public ResponseEntity<ResetPasswordResponse> resetPassword(@Valid @RequestBody ResetPasswordRequest request) {
        authService.resetPassword(request);
        return ResponseEntity.ok(ResetPasswordResponse.success());
    }

    /**
     * 회원탈퇴
     */
    @Operation(summary = "회원탈퇴", description = "비밀번호 확인 후 회원탈퇴 처리")
    @PostMapping("/delete-account")
    public ResponseEntity<ApiResponse<DeleteAccountResponse>> deleteAccount(
            @Valid @RequestBody DeleteAccountRequest request) {
        Integer userId = SecurityUtil.getCurrentUserId();
        Integer deletedUserId = authService.deleteAccount(request, userId);
        return ResponseEntity.ok(ApiResponse.success(DeleteAccountResponse.of(deletedUserId), "회원탈퇴 완료"));
    }

    /**
     * 비밀번호 재설정 (A형 - 복지카드 인증)
     */
    @Operation(summary = "비밀번호 재설정 (Blind)", description = "복지카드 인증 후 비밀번호 재설정 (A형 전용)")
    @PostMapping("/resetPasswordBlind")
    public ResponseEntity<ResetPasswordResponse> resetPasswordBlind(
            @Valid @RequestBody ResetPasswordByWelfareRequest request) {
        authService.resetPasswordByWelfare(request);
        return ResponseEntity.ok(ResetPasswordResponse.success());
    }
}
