package com.ssafy.d108.backend.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "platforms")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Platform {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "platform_name", length = 50, unique = true, nullable = false)
    private String platformName;

    @Column(name = "base_url", length = 500, nullable = false)
    private String baseUrl;

    public Platform(String platformName, String baseUrl) {
        this.platformName = platformName;
        this.baseUrl = baseUrl;
    }
}