package com.ssafy.d108.backend.global.exception;

import com.ssafy.d108.backend.global.response.ErrorCode;

/**
 * 주문을 찾을 수 없을 때 발생하는 예외
 */
public class OrderNotFoundException extends BusinessException {

    public OrderNotFoundException() {
        super(ErrorCode.ORDER_NOT_FOUND);
    }

    public OrderNotFoundException(Integer orderId) {
        super(ErrorCode.ORDER_NOT_FOUND, "주문 내역을 찾을 수 없습니다. ID: " + orderId);
    }
}
