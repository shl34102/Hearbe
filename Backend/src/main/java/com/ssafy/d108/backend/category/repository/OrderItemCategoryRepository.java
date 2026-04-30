package com.ssafy.d108.backend.category.repository;

import com.ssafy.d108.backend.entity.OrderItemCategory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * OrderItemCategory Repository
 */
@Repository
public interface OrderItemCategoryRepository extends JpaRepository<OrderItemCategory, Integer> {

    /**
     * 특정 OrderItem과 관련된 모든 OrderItemCategory 조회
     * 
     * @param orderItemId OrderItem ID
     * @return OrderItemCategory 리스트
     */
    List<OrderItemCategory> findByOrderItemId(Integer orderItemId);

    /**
     * 특정 Category와 관련된 모든 OrderItemCategory 조회
     * 
     * @param categoryId Category ID
     * @return OrderItemCategory 리스트
     */
    List<OrderItemCategory> findByCategoryId(Integer categoryId);

    /**
     * 사용자와 카테고리로 OrderItemCategory 조회
     * 
     * @param userId     사용자 ID
     * @param categoryId 카테고리 ID
     * @return OrderItemCategory 리스트
     */
    @Query("SELECT oic FROM OrderItemCategory oic WHERE oic.orderItem.user.id = :userId AND oic.category.id = :categoryId")
    List<OrderItemCategory> findByUserIdAndCategoryId(@Param("userId") Integer userId,
            @Param("categoryId") Integer categoryId);
}
