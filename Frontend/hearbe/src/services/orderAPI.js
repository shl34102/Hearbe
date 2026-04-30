// 주문내역 API
// A형과 C형에서 공통 사용

import { apiClient, API_BASE_URL } from './apiClient.js';

// Helper function to get auth token
const getAuthToken = () => {
    return localStorage.getItem('accessToken');
};

// Helper function to get auth header
const getAuthHeader = () => {
    const token = getAuthToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// 공통 에러 핸들링
const handleResponse = async (response) => {
    if (!response.ok) {
        if (response.status === 401) {
            throw new Error('로그인이 필요합니다.');
        }
        if (response.status === 403) {
            throw new Error('접근 권한이 없습니다.');
        }
        if (response.status === 404) {
            throw new Error('주문내역을 찾을 수 없습니다.');
        }
        if (response.status >= 500) {
            throw new Error('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        }
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || '요청이 실패했습니다.');
    }
    return await response.json();
};

// Order API Service
export const orderAPI = {
    /**
     * 주문내역 조회
     * GET /orders/me
     *
     * @returns {Promise<Object>} 주문내역 데이터
     *
     * Response 구조:
     * {
     *   code: 200,
     *   message: "성공적으로 처리되었습니다.",
     *   data: {
     *     orders: [
     *       {
     *         order_id: number,
     *         ordered_at: string (YYYY-MM-DD),
     *         order_url: string,
     *         platform_id: number (1:쿠팡, 2:네이버, 3:11번가, 4:SSG),
     *         items: [
     *           {
     *             name: string,
     *             price: number,
     *             quantity: number,
     *             url: string,
     *             img_url: string,
     *             deliver_url: string | null
     *           }
     *         ]
     *       }
     *     ]
     *   }
     * }
     */
    getOrders: async () => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/orders/me`, {
                method: 'GET',
                headers: {
                    ...getAuthHeader(),
                },
            });

            return await handleResponse(response);
        } catch (error) {
            // Network error handling
            if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
                throw new Error('네트워크 연결을 확인해주세요.');
            }
            console.error('getOrders API Error:', error);
            throw error;
        }
    },

    /**
     * 주문 생성 (결제 완료 후 주문 내역 저장)
     * POST /orders
     * @param {Object} orderData - 주문 데이터 (platform_id, order_url, items 등)
     * @returns {Promise<Object>} 생성된 주문 결과
     */
    createOrder: async (orderData) => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/orders`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader(),
                },
                body: JSON.stringify(orderData),
            });

            return await handleResponse(response);
        } catch (error) {
            console.error('createOrder API Error:', error);
            throw error;
        }
    },
};
