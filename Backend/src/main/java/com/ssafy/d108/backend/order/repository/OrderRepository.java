package com.ssafy.d108.backend.order.repository;

import com.ssafy.d108.backend.entity.Order;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<Order, Integer> {
        List<Order> findAllByUserIdOrderByCreatedAtDesc(Integer userId);

        @Modifying
        @Query("DELETE FROM Order o WHERE o.user.id = :userId")
        void deleteAllByUserId(@Param("userId") Integer userId);
}
