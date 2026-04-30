package com.ssafy.d108.backend.global.util;

import com.ssafy.d108.backend.entity.Platform;
import com.ssafy.d108.backend.platform.repository.PlatformRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final PlatformRepository platformRepository;

    @Override
    public void run(String... args) {
        if (platformRepository.count() == 0) { // 데이터가 없을 때만 실행
            platformRepository.save(new Platform("COUPANG", "https://coupang.com"));
            platformRepository.save(new Platform("NAVER", "https://naver.com"));
            System.out.println("초기 플랫폼 데이터가 삽입되었습니다.");
        }
    }
}