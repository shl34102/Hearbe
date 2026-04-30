package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 찜한 상품을 찾을 수 없을 때 발생하는 예외
 */
public class WishlistItemNotFoundException extends BusinessException {

    public WishlistItemNotFoundException() {
        super(ErrorCode.WISHLIST_ITEM_NOT_FOUND);
    }

    public WishlistItemNotFoundException(Integer wishlistItemId) {
        super(ErrorCode.WISHLIST_ITEM_NOT_FOUND, "찜한 상품을 찾을 수 없습니다. ID: " + wishlistItemId);
    }
}
