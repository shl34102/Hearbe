package com.ssafy.d108.backend.cartItem.repository;

import com.ssafy.d108.backend.entity.CartItem;
import com.ssafy.d108.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CartItemRepository extends JpaRepository<CartItem, Integer> {

    /**
     * 특정 사용자의 모든 장바구니 아이템을 최신순으로 조회
     * @param user 사용자 엔티티
     * @return 장바구니 아이템 리스트
     */
    List<CartItem> findAllByUser(User user);

    /**
     * 특정 사용자의 장바구니 아이템 전체 삭제 (장바구니 비우기)
     */
    void deleteAllByUser(User user);

    @Modifying
    @Query("DELETE FROM CartItem c WHERE c.user.id = :userId")
    void deleteAllByUserId(@Param("userId") Integer userId);
}