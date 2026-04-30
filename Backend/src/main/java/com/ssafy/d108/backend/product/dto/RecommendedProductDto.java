package com.ssafy.d108.backend.product.dto;

import com.ssafy.d108.backend.entity.OrderItem;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 추천 상품 정보 DTO
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class RecommendedProductDto {

    /**
     * 상품명
     */
    private String name;

    /**
     * 사용자가 이 상품을 구매한 횟수
     */
    private Integer purchaseCount;

    /**
     * 카테고리 매칭 정보
     * 예: "동일 상품명", "카테고리 일치 (식품/생수/음료)"
     */
    private String categoryMatch;

    /**
     * 쿠팡 상품 번호 (있을 경우)
     */
    private String coupangProductNumber;

    /**
     * OrderItem으로부터 RecommendedProductDto 생성
     * 
     * @param name          상품명
     * @param purchaseCount 구매 횟수
     * @param categoryMatch 카테고리 매칭 정보
     * @return RecommendedProductDto
     */
    public static RecommendedProductDto of(String name, int purchaseCount, String categoryMatch) {
        RecommendedProductDto dto = new RecommendedProductDto();
        dto.setName(name);
        dto.setPurchaseCount(purchaseCount);
        dto.setCategoryMatch(categoryMatch);
        return dto;
    }

    /**
     * OrderItem과 추가 정보로부터 RecommendedProductDto 생성
     * 
     * @param item          OrderItem 엔티티
     * @param purchaseCount 구매 횟수
     * @param categoryMatch 카테고리 매칭 정보
     * @return RecommendedProductDto
     */
    public static RecommendedProductDto from(OrderItem item, int purchaseCount, String categoryMatch) {
        RecommendedProductDto dto = new RecommendedProductDto();
        dto.setName(item.getName());
        dto.setPurchaseCount(purchaseCount);
        dto.setCategoryMatch(categoryMatch);
        dto.setCoupangProductNumber(item.getCoupangProductNumber());
        return dto;
    }
}
