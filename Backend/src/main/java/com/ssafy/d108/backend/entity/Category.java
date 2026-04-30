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
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

/**
 * 상품 카테고리 엔티티
 * 쿠팡 등의 쇼핑몰에서 제공하는 카테고리 경로를 저장
 * 예: ["식품", "사과식초/땅콩버터 외", "생수/음료", "생수", "국산생수"]
 */
@Entity
@Table(name = "categories")
@Getter
@Setter
@NoArgsConstructor
public class Category {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Integer id;

    /**
     * 카테고리 계층 레벨 (0부터 시작)
     * 예: "식품" = 0, "사과식초/땅콩버터 외" = 1, "생수/음료" = 2, ...
     */
    @Column(name = "level", nullable = false)
    private Integer level;

    /**
     * 해당 레벨에서의 카테고리 이름
     * 예: "식품", "생수/음료", "국산생수" 등
     */
    @Column(name = "name", length = 255, nullable = false)
    private String name;

    /**
     * 전체 카테고리 경로 (구분자: "/")
     * 예: "식품/사과식초/땅콩버터 외/생수/음료/생수/국산생수"
     * 중복 방지 및 빠른 검색을 위해 unique 제약조건 추가 필요
     */
    @Column(name = "full_path", length = 1000, nullable = false, unique = true)
    private String fullPath;

    /**
     * 이 카테고리를 참조하는 주문 아이템 카테고리 관계들 (One-to-Many)
     */
    @OneToMany(mappedBy = "category", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<OrderItemCategory> orderItemCategories = new ArrayList<>();

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /**
     * 카테고리 경로 배열로부터 Category 엔티티 생성
     * 
     * @param categoryPath 카테고리 경로 배열
     * @param level        현재 레벨
     * @return Category 엔티티
     */
    public static Category from(String[] categoryPath, int level) {
        Category category = new Category();
        category.setLevel(level);
        category.setName(categoryPath[level]);

        // fullPath 생성: 0번부터 현재 레벨까지 "/"로 연결
        StringBuilder pathBuilder = new StringBuilder();
        for (int i = 0; i <= level; i++) {
            if (i > 0) {
                pathBuilder.append("/");
            }
            pathBuilder.append(categoryPath[i]);
        }
        category.setFullPath(pathBuilder.toString());

        return category;
    }
}
