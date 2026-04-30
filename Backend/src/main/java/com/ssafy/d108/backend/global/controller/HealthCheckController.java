package com.ssafy.d108.backend.global.controller;

import com.ssafy.d108.backend.global.response.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Health Check 컨트롤러
 * 서버 상태 확인 및 모니터링을 위한 엔드포인트 제공
 */
@RestController
// @RequestMapping("/api") // Removed class level mapping to allow root mapping
public class HealthCheckController {

    /**
     * 기본 Health Check 엔드포인트
     * 
     * @return 서버 상태 정보
     */
    @GetMapping("/health")
    public ApiResponse<Map<String, Object>> health() {
        Map<String, Object> healthData = new HashMap<>();
        healthData.put("status", "UP");
        healthData.put("timestamp", LocalDateTime.now());
        healthData.put("service", "HearBe-backend");

        return ApiResponse.success(healthData, "서버가 정상적으로 동작 중입니다.");
    }

    /**
     * 간단한 Health Check (로드밸런서용)
     * 
     * @return OK 문자열
     */
    @GetMapping("/ping")
    public String ping() {
        return "OK";
    }

    /**
     * 루트 경로 확인 (사용자 편의성)
     * 
     * @return 환영 메시지
     */
    @GetMapping("/")
    public String root() {
        return "HearBe Server is running on port 8080!";
    }
}
