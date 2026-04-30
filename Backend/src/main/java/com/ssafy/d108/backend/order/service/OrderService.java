package com.ssafy.d108.backend.order.service;

import com.ssafy.d108.backend.auth.repository.UserRepository;
import com.ssafy.d108.backend.category.repository.CategoryRepository;
import com.ssafy.d108.backend.entity.Category;
import com.ssafy.d108.backend.entity.Order;
import com.ssafy.d108.backend.entity.OrderItem;
import com.ssafy.d108.backend.entity.Platform;
import com.ssafy.d108.backend.entity.User;
import com.ssafy.d108.backend.global.exception.BusinessException;
import com.ssafy.d108.backend.global.response.ErrorCode;
import com.ssafy.d108.backend.order.dto.OrderCreateRequest;
import com.ssafy.d108.backend.order.dto.OrderItemResponse;
import com.ssafy.d108.backend.order.dto.OrderListResponse;
import com.ssafy.d108.backend.order.dto.OrderResponse;
import com.ssafy.d108.backend.order.repository.OrderItemRepository;
import com.ssafy.d108.backend.order.repository.OrderRepository;
import com.ssafy.d108.backend.platform.repository.PlatformRepository;
import com.ssafy.d108.backend.product.dto.RecommendedProductDto;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {

    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final UserRepository userRepository;
    private final PlatformRepository platformRepository;
    private final CategoryRepository categoryRepository;
    private final com.ssafy.d108.backend.product.service.ProductRecommendationService productRecommendationService;

    /**
     * 주문 생성 (다중 상품 주문)
     */
    @Transactional
    public OrderResponse createOrder(Integer userId, OrderCreateRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));

        Platform platform = platformRepository.findById(request.getPlatformId().intValue())
                .orElseThrow(() -> new BusinessException(ErrorCode.PLATFORM_NOT_FOUND));

        // 1. Order 생성
        Order order = new Order();
        order.setUser(user);
        // orderDetailUrl은 request의 order_url 사용
        if (request.getOrderUrl() != null) {
            order.setOrderDetailUrl(request.getOrderUrl());
        }

        // Save Order
        Order savedOrder = orderRepository.save(order);

        // 2. 여러 OrderItem 생성
        List<OrderItem> savedItems = new ArrayList<>();
        for (com.ssafy.d108.backend.order.dto.OrderItemDto itemDto : request.getItems()) {
            OrderItem orderItem = new OrderItem();
            orderItem.setOrder(savedOrder);
            orderItem.setUser(user);
            orderItem.setPlatform(platform);
            orderItem.setName(itemDto.getName());
            orderItem.setPrice(itemDto.getPrice());
            orderItem.setQuantity(itemDto.getQuantity());
            orderItem.setUrl(itemDto.getUrl());
            orderItem.setImgUrl(itemDto.getImgUrl());
            orderItem.setDeliverUrl(itemDto.getDeliverUrl());

            if (itemDto.getCoupangProductNumber() != null) {
                orderItem.setCoupangProductNumber(itemDto.getCoupangProductNumber());
            }

            if (itemDto.getCategoryPath() != null && !itemDto.getCategoryPath().isEmpty()) {
                String[] categoryArray = itemDto.getCategoryPath().toArray(new String[0]);

                for (int level = 0; level < categoryArray.length; level++) {
                    Category category = Category.from(categoryArray, level);

                    Category existingCategory = categoryRepository.findByFullPath(category.getFullPath())
                            .orElseGet(() -> categoryRepository.save(category));

                    orderItem.addCategory(existingCategory);
                }
            }

            savedItems.add(orderItemRepository.save(orderItem));
        }

        List<OrderItemResponse> itemResponses = savedItems.stream()
                .map(OrderItemResponse::from)
                .collect(Collectors.toList());

        return OrderResponse.of(savedOrder, itemResponses);
    }

    public OrderListResponse getMyOrders(Integer userId) {
        List<Order> orders = orderRepository.findAllByUserIdOrderByCreatedAtDesc(userId);

        List<OrderListResponse.OrderDetailDto> orderDtos = orders.stream()
                .map(order -> {
                    List<OrderItem> items = orderItemRepository.findAllByOrderId(order.getId());

                    if (items.isEmpty()) {
                        return null;
                    }

                    List<OrderItemResponse> itemResponses = items.stream()
                            .map(OrderItemResponse::from)
                            .collect(Collectors.toList());

                    Long extractedPlatformId = Long.valueOf(items.get(0).getPlatform().getId());

                    return OrderListResponse.OrderDetailDto.from(order, itemResponses, extractedPlatformId);
                })
                .filter(dto -> dto != null)
                .collect(Collectors.toList());

        // 추천 상품 생성 - 사용자의 전체 주문 이력 기반으로 추천
        List<RecommendedProductDto> recommendations = productRecommendationService
                .generateRecommendationsForUser(userId);

        return new OrderListResponse(orderDtos, recommendations);
    }
}
