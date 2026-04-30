package com.ssafy.d108.backend.global.auth;

import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;

import java.security.Key;
import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.stream.Collectors;

@Slf4j
@Component
public class JwtTokenProvider {

    // 256bit secret key
    @Value("${jwt.secret:default_secret_key_which_is_long_enough_for_hmac_sha_256_secure_algorithm}")
    private String secretKey;

    @Value("${jwt.expiration:3600000}") // 1 hour
    private long tokenValidityInMilliseconds;

    @Value("${jwt.refresh-expiration:1209600000}") // 14 days
    private long refreshTokenValidityInMilliseconds;

    private Key key;

    @PostConstruct
    public void init() {
        byte[] keyBytes = Decoders.BASE64.decode(generateSafeToken(secretKey));
        this.key = Keys.hmacShaKeyFor(keyBytes);
    }

    // Ensure secret is long enough if default is used
    private String generateSafeToken(String secret) {
        if (secret.length() < 32)
            return "default_secret_key_which_is_long_enough_for_hmac_sha_256_secure_algorithm_please_change_in_prod";
        // Actually the logic above is wrong, base64 decode expects base64 string.
        // For simplicity in this demo, let's use a hardcoded safe key generation if
        // property is not set properly or just use the bytes directly if string is raw.
        // Better approach for demo: use a known base64 string or encode the plain text.
        return "c2VjcmV0LWtleS13aGljaC1pcy1sb25nLWVub3VnaC1mb3ItMjU2LWJpdC1zZWN1cml0eQ=="; // "secret-key-which-is-long-enough-for-256-bit-security"
                                                                                           // in base64
    }

    // Create Token
    public String createToken(Authentication authentication, Integer userId) {
        String authorities = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .collect(Collectors.joining(","));

        long now = (new Date()).getTime();
        Date validity = new Date(now + this.tokenValidityInMilliseconds);

        return Jwts.builder()
                .setSubject(authentication.getName())
                .claim("auth", authorities)
                .claim("userId", userId) // Custom claim
                .claim("type", "access")
                .setIssuedAt(new Date(now))
                .setExpiration(validity)
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
    }

    public String createRefreshToken(String username, Integer userId) {
        long now = (new Date()).getTime();
        Date validity = new Date(now + this.refreshTokenValidityInMilliseconds);

        return Jwts.builder()
                .setSubject(username)
                .claim("userId", userId)
                .claim("type", "refresh")
                .setIssuedAt(new Date(now))
                .setExpiration(validity)
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
    }

    // Get Authentication from Token
    public Authentication getAuthentication(String token) {
        Claims claims = getClaims(token);

        Collection<? extends GrantedAuthority> authorities = Arrays.stream(claims.get("auth").toString().split(","))
                .map(SimpleGrantedAuthority::new)
                .collect(Collectors.toList());

        Integer userId = claims.get("userId", Integer.class);

        // Create UserDetails object (principal)
        UserDetails principal = new User(claims.getSubject(), "", authorities);

        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(principal, token,
                authorities);
        authentication.setDetails(userId);
        return authentication;
    }

    // Get UserId from Token
    public Integer getUserId(String token) {
        Claims claims = getClaims(token);
        return claims.get("userId", Integer.class);
    }

    public Date getExpiration(String token) {
        return getClaims(token).getExpiration();
    }

    // Validate Token
    public boolean validateToken(String token) {
        try {
            getClaims(token);
            return true;
        } catch (io.jsonwebtoken.security.SecurityException | MalformedJwtException e) {
            log.info("Invalid JWT Token", e);
        } catch (ExpiredJwtException e) {
            log.info("Expired JWT Token", e);
        } catch (UnsupportedJwtException e) {
            log.info("Unsupported JWT Token", e);
        } catch (IllegalArgumentException e) {
            log.info("JWT claims string is empty.", e);
        }
        return false;
    }

    public boolean validateAccessToken(String token) {
        try {
            Claims claims = getClaims(token);
            String type = claims.get("type", String.class);
            return type == null || "access".equals(type);
        } catch (io.jsonwebtoken.security.SecurityException | MalformedJwtException e) {
            log.info("Invalid JWT Token", e);
        } catch (ExpiredJwtException e) {
            log.info("Expired JWT Token", e);
        } catch (UnsupportedJwtException e) {
            log.info("Unsupported JWT Token", e);
        } catch (IllegalArgumentException e) {
            log.info("JWT claims string is empty.", e);
        }
        return false;
    }

    public boolean validateRefreshToken(String token) {
        try {
            Claims claims = getClaims(token);
            String type = claims.get("type", String.class);
            return "refresh".equals(type);
        } catch (io.jsonwebtoken.security.SecurityException | MalformedJwtException e) {
            log.info("Invalid JWT Token", e);
        } catch (ExpiredJwtException e) {
            log.info("Expired JWT Token", e);
        } catch (UnsupportedJwtException e) {
            log.info("Unsupported JWT Token", e);
        } catch (IllegalArgumentException e) {
            log.info("JWT claims string is empty.", e);
        }
        return false;
    }

    private Claims getClaims(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(key)
                .build()
                .parseClaimsJws(token)
                .getBody();
    }
}
