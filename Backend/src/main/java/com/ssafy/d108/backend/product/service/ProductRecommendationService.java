package com.ssafy.d108.backend.product.service;

import com.ssafy.d108.backend.entity.OrderItem;
import com.ssafy.d108.backend.order.repository.OrderItemRepository;
import com.ssafy.d108.backend.product.dto.ProductRecommendationResponse;
import com.ssafy.d108.backend.product.dto.RecommendedProductDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductRecommendationService {

    private final OrderItemRepository orderItemRepository;

    private static final int THRESHOLD_SAME_PRODUCT = 3;
    private static final int THRESHOLD_CATEGORY_MATCH = 3;
    private static final int MIN_CATEGORY_DEPTH_MATCH = 2;

    public ProductRecommendationResponse getRecommendations(
            Integer userId,
            String productName,
            List<String> categoryPath) {
        log.info("상품 추천 시작: userId={}, productName={}, categoryPath={}",
                userId, productName, categoryPath);

        Map<String, RecommendedProductDto> recommendationMap = new HashMap<>();

        List<OrderItem> sameProductItems = orderItemRepository.findByUserIdAndProductName(userId, productName);
        int sameProductCount = sameProductItems.size();

        log.debug("동일 상품명 구매 횟수: {}", sameProductCount);

        if (sameProductCount >= THRESHOLD_SAME_PRODUCT) {
            RecommendedProductDto dto = RecommendedProductDto.of(
                    productName,
                    sameProductCount,
                    "동일 상품명 " + sameProductCount + "회 구매");
            if (!sameProductItems.isEmpty() && sameProductItems.get(0).getCoupangProductNumber() != null) {
                dto.setCoupangProductNumber(sameProductItems.get(0).getCoupangProductNumber());
            }
            recommendationMap.put(productName, dto);
            log.info("추천 추가 (동일 상품명): {}, 구매횟수: {}", productName, sameProductCount);
        }

        if (categoryPath != null && categoryPath.size() >= MIN_CATEGORY_DEPTH_MATCH) {
            StringBuilder categoryPrefix = new StringBuilder();
            for (int i = 0; i < Math.min(categoryPath.size(), MIN_CATEGORY_DEPTH_MATCH); i++) {
                if (i > 0) {
                    categoryPrefix.append("/");
                }
                categoryPrefix.append(categoryPath.get(i));
            }
            String categoryPrefixStr = categoryPrefix.toString();

            log.debug("카테고리 prefix 검색: {}", categoryPrefixStr);

            List<Object[]> frequentProducts = orderItemRepository.findFrequentProductsByCategoryPrefix(
                    userId,
                    categoryPrefixStr,
                    THRESHOLD_CATEGORY_MATCH);

            log.debug("유사 카테고리 상품 개수: {}", frequentProducts.size());

            for (Object[] row : frequentProducts) {
                String name = (String) row[0];
                Long countLong = (Long) row[1];
                int count = countLong.intValue();

                if (!recommendationMap.containsKey(name)) {
                    RecommendedProductDto dto = RecommendedProductDto.of(
                            name,
                            count,
                            "유사 카테고리 상품 " + count + "회 구매 (" + categoryPrefixStr + ")");

                    List<OrderItem> items = orderItemRepository.findByUserIdAndProductName(userId, name);
                    if (!items.isEmpty() && items.get(0).getCoupangProductNumber() != null) {
                        dto.setCoupangProductNumber(items.get(0).getCoupangProductNumber());
                    }

                    recommendationMap.put(name, dto);
                    log.info("추천 추가 (유사 카테고리): {}, 구매횟수: {}", name, count);
                }
            }
        }

        List<RecommendedProductDto> sortedRecommendations = recommendationMap.values().stream()
                .sorted(Comparator.comparing(RecommendedProductDto::getPurchaseCount).reversed())
                .collect(Collectors.toList());

        String criteria = String.format(
                "동일 상품명 %d회 이상 구매 또는 유사 카테고리 상품 %d회 이상 구매 (최소 %d단계 카테고리 일치)",
                THRESHOLD_SAME_PRODUCT,
                THRESHOLD_CATEGORY_MATCH,
                MIN_CATEGORY_DEPTH_MATCH);

        log.info("추천 완료: userId={}, 추천 상품 개수={}", userId, sortedRecommendations.size());

        return ProductRecommendationResponse.of(sortedRecommendations, criteria);
    }

    public List<RecommendedProductDto> generateRecommendationsForUser(Integer userId) {
        log.info("사용자 추천 생성 시작: userId={}", userId);

        Map<String, RecommendedProductDto> recommendationMap = new HashMap<>();

        List<Object[]> frequentProducts = orderItemRepository.findFrequentProductsByCategoryPrefix(
                userId,
                "",
                THRESHOLD_SAME_PRODUCT);

        log.debug("자주 구매한 상품 개수: {}", frequentProducts.size());

        for (Object[] row : frequentProducts) {
            String productName = (String) row[0];
            Long countLong = (Long) row[1];
            int count = countLong.intValue();

            RecommendedProductDto dto = RecommendedProductDto.of(
                    productName,
                    count,
                    count + "회 구매");

            List<OrderItem> items = orderItemRepository.findByUserIdAndProductName(userId, productName);
            if (!items.isEmpty() && items.get(0).getCoupangProductNumber() != null) {
                dto.setCoupangProductNumber(items.get(0).getCoupangProductNumber());
            }

            recommendationMap.put(productName, dto);
        }

        List<RecommendedProductDto> recommendations = recommendationMap.values().stream()
                .sorted(Comparator.comparing(RecommendedProductDto::getPurchaseCount).reversed())
                .collect(Collectors.toList());

        log.info("사용자 추천 완료: userId={}, 추천 상품 개수={}", userId, recommendations.size());

        return recommendations;
    }
}
