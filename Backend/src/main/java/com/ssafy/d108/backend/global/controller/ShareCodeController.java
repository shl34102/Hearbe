package com.ssafy.d108.backend.global.controller;

import com.ssafy.d108.backend.global.service.ShareCodeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/share")
@RequiredArgsConstructor
@CrossOrigin(origins = "*", allowedHeaders = "*")
public class ShareCodeController {

    private final ShareCodeService shareCodeService;

    /**
     * 공유 코드 생성 (A형 User용)
     */
    @PostMapping("/code")
    public ResponseEntity<Map<String, String>> createShareCode() {
        // Session ID is strictly not needed for PeerJS flow, but we can store "valid"
        // or user IP/ID
        String code = shareCodeService.generateShareCode("valid");
        return ResponseEntity.ok(Map.of("code", code));
    }

    /**
     * 공유 코드 검증 (S형 Guardian용)
     */
    @GetMapping("/code/{code}")
    public ResponseEntity<Map<String, Object>> validateShareCode(@PathVariable String code) {
        String value = shareCodeService.getSessionId(code);

        if (value != null) {
            return ResponseEntity.ok(Map.of("valid", true, "message", "Valid code"));
        } else {
            return ResponseEntity.status(404).body(Map.of("valid", false, "message", "Invalid or expired code"));
        }
    }
}
