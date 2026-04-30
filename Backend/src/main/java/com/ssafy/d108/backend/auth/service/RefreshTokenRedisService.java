package com.ssafy.d108.backend.auth.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class RefreshTokenRedisService {

    private static final String KEY_PREFIX = "refresh:";

    private final StringRedisTemplate stringRedisTemplate;

    public void save(Integer userId, String refreshToken, Date expiration) {
        String key = buildKey(userId);
        long ttlSeconds = getTtlSeconds(expiration);
        stringRedisTemplate.opsForValue().set(key, hash(refreshToken), Duration.ofSeconds(ttlSeconds));
    }

    public boolean matches(Integer userId, String refreshToken) {
        String storedHash = stringRedisTemplate.opsForValue().get(buildKey(userId));
        if (storedHash == null) {
            return false;
        }
        return storedHash.equals(hash(refreshToken));
    }

    public void delete(Integer userId) {
        stringRedisTemplate.delete(buildKey(userId));
    }

    private String buildKey(Integer userId) {
        return KEY_PREFIX + userId;
    }

    private long getTtlSeconds(Date expiration) {
        long seconds = Duration.between(Instant.now(), expiration.toInstant()).getSeconds();
        return Math.max(seconds, 1);
    }

    private String hash(String refreshToken) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashed = digest.digest(refreshToken.getBytes(StandardCharsets.UTF_8));
            return toHex(hashed);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }

    private String toHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
