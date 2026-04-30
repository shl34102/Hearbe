package com.ssafy.d108.backend.entity.enums;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

/**
 * 알레르기 유발 물질 (간소화 버전 6종)
 */
@Getter
@RequiredArgsConstructor
public enum Allergy {
    NUTS("견과류"),
    DAIRY("유제품"),
    WHEAT("밀"),
    BEAN("콩"),
    SEAFOOD("해산물"),
    EGG("달걀");

    private final String description;
}
