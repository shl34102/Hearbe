package com.ssafy.d108.backend.global.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Random;

@Slf4j
@Service
@RequiredArgsConstructor
public class ShareCodeService {

    private final StringRedisTemplate redisTemplate;
    private static final String CODE_PREFIX = "share:";
    private static final long CODE_EXPIRATION_MINUTES = 3;

    public String generateShareCode(String sessionId) {
        String code = generateRandomCode();
        // Ensure uniqueness (simple retry logic)
        while (Boolean.TRUE.equals(redisTemplate.hasKey(CODE_PREFIX + code))) {
            code = generateRandomCode();
        }

        // Save Code -> SessionId (or "valid")
        String value = (sessionId != null) ? sessionId : "valid";
        redisTemplate.opsForValue().set(CODE_PREFIX + code, value, Duration.ofMinutes(CODE_EXPIRATION_MINUTES));

        log.info("Generated Share Code: {} (valid for {} mins)", code, CODE_EXPIRATION_MINUTES);
        return code;
    }

    public String getSessionId(String code) {
        if (code == null)
            return null;
        return redisTemplate.opsForValue().get(CODE_PREFIX + code);
    }

    private String generateRandomCode() {
        Random random = new Random();
        int number = 1000 + random.nextInt(9000); // 1000 ~ 9999 (4 digits)
        return String.valueOf(number);
    }
}
