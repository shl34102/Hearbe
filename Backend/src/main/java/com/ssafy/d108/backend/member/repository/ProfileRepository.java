package com.ssafy.d108.backend.member.repository;

import com.ssafy.d108.backend.entity.Profile;
import com.ssafy.d108.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ProfileRepository extends JpaRepository<Profile, Integer> {
    Optional<Profile> findByUser(User user);

    Optional<Profile> findByUserId(Integer userId);

    @Modifying
    @Query("DELETE FROM Profile p WHERE p.user.id = :userId")
    void deleteByUserId(@Param("userId") Integer userId);
}
