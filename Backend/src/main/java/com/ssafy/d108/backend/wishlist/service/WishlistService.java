package com.ssafy.d108.backend.wishlist.service;

import com.ssafy.d108.backend.auth.repository.UserRepository;
import com.ssafy.d108.backend.entity.Platform;
import com.ssafy.d108.backend.entity.User;
import com.ssafy.d108.backend.entity.WishlistItem; // 엔티티 클래스명 확인 필요
import com.ssafy.d108.backend.global.exception.BusinessException;
import com.ssafy.d108.backend.global.response.ErrorCode;
import com.ssafy.d108.backend.platform.repository.PlatformRepository;
import com.ssafy.d108.backend.wishlist.dto.*;
import com.ssafy.d108.backend.wishlist.repository.WishlistRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class WishlistService {

    private final WishlistRepository wishlistRepository;
    private final UserRepository userRepository;
    private final PlatformRepository platformRepository;

    /**
     * 찜 추가 (POST /wishlist)
     */
    @Transactional
    public WishlistCreateResponse addWishlistItem(Integer userId, WishlistCreateRequest requestDto) {
        User user = findUserById(userId);
        Platform platform = platformRepository.findById(requestDto.getPlatformId().intValue())
                .orElseThrow(() -> new BusinessException(ErrorCode.PLATFORM_NOT_FOUND));

        WishlistItem wishlistItem = createWishlistEntity(user, platform, requestDto);
        WishlistItem savedItem = wishlistRepository.save(wishlistItem);

        return new WishlistCreateResponse(savedItem.getId(), savedItem.getCreatedAt().toString());
    }

    /**
     * 찜 목록 조회 (GET /wishlist/{userId})
     */
    public WishlistResponse getWishlistItems(Integer userId) {
        User user = findUserById(userId);
        List<WishlistItem> items = wishlistRepository.findAllByUser(user);

        // 1. 개별 아이템 상세 정보 리스트 변환
        List<WishlistResponse.WishlistItemDetail> itemDetails = items.stream()
                .map(this::convertToDetailDto)
                .collect(Collectors.toList());

        // 2. 비즈니스 로직: 총 개수 및 총 가격 계산
        int totalCount = items.size();
        long totalPrice = items.stream()
                .mapToLong(WishlistItem::getPrice) // Entity에 getPrice()가 있다고 가정
                .sum();

        // 3. 최종 Response 조립
        WishlistResponse response = new WishlistResponse();
        response.setItems(itemDetails);
        response.setTotalCount(totalCount);
        response.setTotalPrice(totalPrice);

        return response;
    }

    /**
     * 찜 삭제 (DELETE /wishlist/{wishlistItemId})
     */
    @Transactional
    public void deleteWishlistItem(Integer wishlistItemId) {
        if (!wishlistRepository.existsById(wishlistItemId)) {
            throw new BusinessException(ErrorCode.WISHLIST_ITEM_NOT_FOUND);
        }
        wishlistRepository.deleteById(wishlistItemId);
    }

    // --- Private Helper Methods ---

    private User findUserById(Integer userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));
    }

    private WishlistItem createWishlistEntity(User user, Platform platform, WishlistCreateRequest dto) {
        WishlistItem item = new WishlistItem();
        item.setUser(user);
        item.setPlatform(platform);
        item.setName(dto.getName());
        item.setUrl(dto.getUrl());
        item.setImgUrl(dto.getImgUrl());
        item.setPrice((long) dto.getPrice());
        return item;
    }

    // helper method 수정
    private WishlistResponse.WishlistItemDetail convertToDetailDto(WishlistItem item) {
        WishlistResponse.WishlistItemDetail detail = new WishlistResponse.WishlistItemDetail();
        detail.setWishlistItemId(item.getId());
        detail.setProductName(item.getName());
        detail.setProductUrl(item.getUrl());
        detail.setPlatformName(item.getPlatform().getPlatformName());
        detail.setCreatedAt(item.getCreatedAt().toString());
        detail.setImgUrl(item.getImgUrl());
        detail.setPrice(item.getPrice()); // 가격 필드 추가
        detail.setLiked(true);
        return detail;
    }
}