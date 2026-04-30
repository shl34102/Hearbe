package com.ssafy.d108.backend.product.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

/**
 * 상품 추천 응답 DTO
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class ProductRecommendationResponse {

    /**
     * 추천 상품 리스트
     */
    private List<RecommendedProductDto> recommendedProducts;

    /**
     * 추천 상품 총 개수
     */
    private Integer totalCount;

    /**
     * 추천 기준 설명
     * 예: "동일 상품명 3회 이상 구매 또는 유사 카테고리 상품 3회 이상 구매"
     */
    private String criteria;

    /**
     * 팩토리 메서드: 추천 결과로부터 응답 생성
     * 
     * @param products 추천 상품 리스트
     * @param criteria 추천 기준
     * @return ProductRecommendationResponse
     */
    public static ProductRecommendationResponse of(List<RecommendedProductDto> products, String criteria) {
        ProductRecommendationResponse response = new ProductRecommendationResponse();
        response.setRecommendedProducts(products);
        response.setTotalCount(products.size());
        response.setCriteria(criteria);
        return response;
    }
}
