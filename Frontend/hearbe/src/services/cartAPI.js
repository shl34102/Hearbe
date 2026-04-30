// A형과 C형에서 공통으로 사용

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

const handleResponse = async (response) => {
    const text = await response.text();
    let data;
    try {
        data = text ? JSON.parse(text) : {};
    } catch (e) {
        console.error('JSON Parse Error:', e);
        data = { message: text };
    }

    if (!response.ok) {
        console.error('================ API ERROR INFO ================');
        console.error('URL:', response.url);
        console.error('Status:', response.status, response.statusText);
        console.error('Body:', data);
        console.error('================================================');

        throw new Error(data.message || `요청 실패 (${response.status})`);
    }
    return data;
};

// Cart API Service
export const cartAPI = {
    /**
     * 장바구니 목록 조회
     * GET /cart
     * @returns {Promise<Object>} 장바구니 데이터
     */
    getCart: async () => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/cart`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader(),
                },
            });

            return await handleResponse(response);
        } catch (error) {
            console.error('getCart API Error:', error);
            throw error;
        }
    },

    /**
     * 장바구니에 상품 추가
     * POST /cart
     * @param {Object} item - 추가할 상품 정보
     * @returns {Promise<Object>} 추가된 상품 데이터
     */
    addCart: async (item) => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/cart`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader(),
                },
                body: JSON.stringify(item),
            });

            return await handleResponse(response);
        } catch (error) {
            console.error('addCart API Error:', error);
            throw error;
        }
    },

    /**
     * 장바구니 상품 수량 변경
     * PATCH /cart/{cartItemId}
     * @param {number|string} cartItemId - 장바구니 아이템 ID
     * @param {number} quantity - 변경할 수량
     * @returns {Promise<Object>} 업데이트된 상품 데이터
     */
    updateCart: async (cartItemId, quantity) => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/cart/${cartItemId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader(),
                },
                body: JSON.stringify({ quantity }),
            });

            return await handleResponse(response);
        } catch (error) {
            console.error('updateCart API Error:', error);
            throw error;
        }
    },

    /**
     * 장바구니 상품 삭제
     * DELETE /cart/{cartItemId}
     * @param {number|string} cartItemId - 장바구니 아이템 ID
     * @returns {Promise<boolean>} 삭제 성공 여부
     */
    deleteCart: async (cartItemId) => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/cart/${cartItemId}`, {
                method: 'DELETE',
                headers: {
                    ...getAuthHeader(),
                },
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || '장바구니 삭제에 실패했습니다.');
            }

            return true;
        } catch (error) {
            console.error('deleteCart API Error:', error);
            throw error;
        }
    },
};
