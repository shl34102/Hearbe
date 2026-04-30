package com.ssafy.d108.backend.wishlist.repository;

import com.ssafy.d108.backend.entity.User;
import com.ssafy.d108.backend.entity.WishlistItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface WishlistRepository extends JpaRepository<WishlistItem, Integer> {

    /**
     * 특정 사용자의 모든 찜 아이템 조회
     */
    List<WishlistItem> findAllByUser(User user);

    /**
     * 특정 사용자의 찜 목록 전체 삭제 (필요 시)
     */
    void deleteAllByUser(User user);

    @Modifying
    @Query("DELETE FROM WishlistItem w WHERE w.user.id = :userId")
    void deleteAllByUserId(@Param("userId") Integer userId);
}