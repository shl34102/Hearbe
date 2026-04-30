package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 장바구니 항목을 찾을 수 없을 때 발생하는 예외
 */
public class CartItemNotFoundException extends BusinessException {

    public CartItemNotFoundException() {
        super(ErrorCode.CART_ITEM_NOT_FOUND);
    }

    public CartItemNotFoundException(Integer cartItemId) {
        super(ErrorCode.CART_ITEM_NOT_FOUND, "장바구니 항목을 찾을 수 없습니다. ID: " + cartItemId);
    }
}
