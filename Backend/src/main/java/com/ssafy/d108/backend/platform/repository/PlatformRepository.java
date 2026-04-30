package com.ssafy.d108.backend.platform.repository;

import com.ssafy.d108.backend.entity.Platform;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PlatformRepository extends JpaRepository<Platform, Integer> {

    Optional<Platform> findByPlatformName(String platformName);
}
