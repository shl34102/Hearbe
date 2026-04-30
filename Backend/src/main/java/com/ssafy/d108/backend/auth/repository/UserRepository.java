package com.ssafy.d108.backend.auth.repository;

import com.ssafy.d108.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * User Repository
 */
@Repository
public interface UserRepository extends JpaRepository<User, Integer> {

    Optional<User> findByUsername(String username);

    boolean existsByUsername(String username);

    boolean existsByPhoneNumber(String phoneNumber);

    // C형: 이름 + 이메일로 사용자 조회 (아이디 찾기)
    Optional<User> findByNameAndEmail(String name, String email);

    // C형: 이메일로 사용자 조회 (비밀번호 재설정)
    Optional<User> findByEmail(String email);
}
