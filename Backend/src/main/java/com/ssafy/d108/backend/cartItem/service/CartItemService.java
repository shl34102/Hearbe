package com.ssafy.d108.backend.cartItem.service;

import com.ssafy.d108.backend.auth.repository.UserRepository;
import com.ssafy.d108.backend.cartItem.dto.*;
import com.ssafy.d108.backend.cartItem.repository.CartItemRepository;
import com.ssafy.d108.backend.global.exception.BusinessException;
import com.ssafy.d108.backend.global.response.ErrorCode;
import com.ssafy.d108.backend.platform.repository.PlatformRepository;
import com.ssafy.d108.backend.entity.CartItem;
import com.ssafy.d108.backend.entity.Platform;
import com.ssafy.d108.backend.entity.User;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class CartItemService {

    private final CartItemRepository cartItemRepository;
    private final PlatformRepository platformRepository;
    private final UserRepository userRepository;

    /**
     * 장바구니 아이템 추가
     */
    @Transactional
    public CartItemCreateResponse addCartItem(Integer userId, CartItemRequest requestDto) {
        User user = findUserById(userId);
        Platform platform = platformRepository.findById(requestDto.getPlatformId().intValue())
                .orElseThrow(() -> new BusinessException(ErrorCode.PLATFORM_NOT_FOUND)); // 공통 에러코드 사용 권장

        CartItem cartItem = createCartItemEntity(user, platform, requestDto);
        CartItem savedItem = cartItemRepository.save(cartItem);

        return new CartItemCreateResponse(savedItem.getId(), "장바구니 추가 완료");
    }

    /**
     * 내 장바구니 목록 조회
     */
    public CartItemListResponse getCartItems(Integer userId) {
        User user = findUserById(userId);
        List<CartItem> items = cartItemRepository.findAllByUser(user);

        List<CartItemListResponse.CartItemDetail> itemDetails = items.stream()
                .map(this::convertToDetailDto)
                .collect(Collectors.toList());

        int totalPrice = (int) items.stream()
                .mapToLong(item -> item.getPrice() * item.getQuantity())
                .sum();

        return buildListResponse(itemDetails, totalPrice);
    }

    /**
     * 장바구니 아이템 수량 수정
     */
    @Transactional
    public CartItemUpdateResponse updateQuantity(Integer cartItemId, CartItemUpdateRequest requestDto) {
        CartItem cartItem = findCartItemById(cartItemId);
        cartItem.setQuantity(requestDto.getQuantity());

        return new CartItemUpdateResponse(Long.valueOf(cartItem.getId()), "수량이 변경되었습니다.");
    }

    /**
     * 장바구니 아이템 개별 삭제
     */
    @Transactional
    public void deleteCartItem(Integer cartItemId) {
        if (!cartItemRepository.existsById(cartItemId)) {
            throw new BusinessException(ErrorCode.CART_ITEM_NOT_FOUND);
        }
        cartItemRepository.deleteById(cartItemId);
    }

    /**
     * 장바구니 전체 비우기
     */
    @Transactional
    public void clearCart(Integer userId) {
        User user = findUserById(userId);
        cartItemRepository.deleteAllByUser(user);
    }

    // --- Private Helper Methods ---

    private User findUserById(Integer userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));
    }

    private CartItem findCartItemById(Integer cartItemId) {
        return cartItemRepository.findById(cartItemId)
                .orElseThrow(() -> new BusinessException(ErrorCode.CART_ITEM_NOT_FOUND));
    }

    private CartItem createCartItemEntity(User user, Platform platform, CartItemRequest dto) {
        CartItem cartItem = new CartItem();
        cartItem.setUser(user);
        cartItem.setPlatform(platform);
        cartItem.setName(dto.getName());
        cartItem.setPrice((long) dto.getPrice());
        cartItem.setImgUrl(dto.getImgUrl());
        cartItem.setUrl(dto.getUrl());
        cartItem.setQuantity(1);
        return cartItem;
    }

    private CartItemListResponse buildListResponse(List<CartItemListResponse.CartItemDetail> details, int totalPrice) {
        CartItemListResponse response = new CartItemListResponse();
        response.setCartItems(details);
        response.setTotalCount(details.size());
        response.setTotalPrice(totalPrice);
        return response;
    }

    private CartItemListResponse.CartItemDetail convertToDetailDto(CartItem item) {
        CartItemListResponse.CartItemDetail detail = new CartItemListResponse.CartItemDetail();
        detail.setCartItemId(Long.valueOf(item.getId()));
        detail.setPlatformId(Long.valueOf(item.getPlatform().getId()));
        detail.setName(item.getName());
        detail.setPrice(item.getPrice().intValue());
        detail.setImgUrl(item.getImgUrl());
        detail.setUrl(item.getUrl());
        detail.setQuantity(item.getQuantity());
        detail.setCreatedAt(item.getCreatedAt().toString());
        return detail;
    }
}