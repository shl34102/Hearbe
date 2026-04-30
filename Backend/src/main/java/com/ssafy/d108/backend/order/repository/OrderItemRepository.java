package com.ssafy.d108.backend.order.repository;

import com.ssafy.d108.backend.entity.OrderItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface OrderItemRepository extends JpaRepository<OrderItem, Integer> {
    List<OrderItem> findAllByOrderId(Integer orderId);

    @Modifying
    @Query("DELETE FROM OrderItem oi WHERE oi.user.id = :userId")
    void deleteAllByUserId(@Param("userId") Integer userId);

    /**
     * 특정 사용자가 특정 상품명으로 구매한 아이템 목록 조회
     * 
     * @param userId      사용자 ID
     * @param productName 상품명
     * @return 해당 상품명으로 구매한 OrderItem 리스트
     */
    @Query("SELECT oi FROM OrderItem oi WHERE oi.user.id = :userId AND oi.name = :productName")
    List<OrderItem> findByUserIdAndProductName(@Param("userId") Integer userId,
            @Param("productName") String productName);

    /**
     * 특정 사용자가 특정 카테고리로 구매한 아이템 목록 조회
     * 
     * @param userId   사용자 ID
     * @param category 카테고리 엔티티
     * @return 해당 카테고리를 포함하는 OrderItem 리스트
     */
    @Query("SELECT DISTINCT oi FROM OrderItem oi JOIN oi.orderItemCategories oic WHERE oi.user.id = :userId AND oic.category = :category")
    List<OrderItem> findByUserIdAndCategory(@Param("userId") Integer userId,
            @Param("category") com.ssafy.d108.backend.entity.Category category);

    /**
     * 카테고리 경로 prefix로 자주 구매한 상품명 조회 (임계값 이상)
     * 
     * @param userId       사용자 ID
     * @param categoryPath 카테고리 경로 prefix (예: "식품/생수")
     * @param minCount     최소 구매 횟수
     * @return [상품명, 구매횟수] 배열 리스트
     */
    @Query("SELECT oi.name, COUNT(DISTINCT oi.id) as cnt FROM OrderItem oi JOIN oi.orderItemCategories oic JOIN oic.category c WHERE oi.user.id = :userId AND c.fullPath LIKE CONCAT(:categoryPath, '%') GROUP BY oi.name HAVING COUNT(DISTINCT oi.id) >= :minCount")
    List<Object[]> findFrequentProductsByCategoryPrefix(@Param("userId") Integer userId,
            @Param("categoryPath") String categoryPath, @Param("minCount") long minCount);
}
