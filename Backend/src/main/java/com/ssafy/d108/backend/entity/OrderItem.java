package com.ssafy.d108.backend.entity;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

@Entity
@Table(name = "order_items")
@Getter
@Setter
@NoArgsConstructor
public class OrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Integer id;

    // 어떤 주문 그룹에 속하는지 (기존 필드 유지)
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    // 누가 주문했는지 (요청하신 user_id)
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    // 어느 플랫폼에서 구매한 상품인지
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "platform_id", nullable = false)
    private Platform platform;

    @Column(name = "name", length = 255, nullable = false)
    private String name;

    @Column(name = "quantity", nullable = false)
    private Integer quantity = 1;

    @Column(name = "url", length = 500)
    private String url;

    @Column(name = "img_url", length = 1000)
    private String imgUrl;

    @Column(name = "price", nullable = false)
    private Long price;

    @Column(name = "deliver_url", length = 1000)
    private String deliverUrl;

    @Column(name = "coupang_product_number", length = 100)
    private String coupangProductNumber;

    @OneToMany(mappedBy = "orderItem", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<OrderItemCategory> orderItemCategories = new ArrayList<>();

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    public void addCategory(Category category) {
        OrderItemCategory orderItemCategory = OrderItemCategory.of(this, category);
        this.orderItemCategories.add(orderItemCategory);
    }
}