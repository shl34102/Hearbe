// 찜 API
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
            throw new Error('찜한 상품을 찾을 수 없습니다.');
        }
        if (response.status >= 500) {
            throw new Error('서버 오류가 발생했습니다.');
        }
        const data = await response.json();
        throw new Error(data.message || '요청이 실패했습니다.');
    }
    return await response.json();
};

// Wishlist API Service
export const wishlistAPI = {
    /**
     * 찜한 상품 목록 조회
     * GET /wishlist
     * @returns {Promise<Object>} 찜 목록 데이터
     */
    getWishlist: async () => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/wishlist`, {
                method: 'GET',
                headers: {
                    ...getAuthHeader(),
                },
            });

            return await handleResponse(response);
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('네트워크 연결을 확인해주세요.');
            }
            console.error('getWishlist API Error:', error);
            throw error;
        }
    },

    /**
     * 찜한 상품 삭제
     * DELETE /wishlist/{wishlistItemId}
     * @param {number|string} wishlistItemId - 찜 아이템 ID
     * @returns {Promise<boolean>} 삭제 성공 여부
     */
    deleteWishlist: async (wishlistItemId) => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/wishlist/${wishlistItemId}`, {
                method: 'DELETE',
                headers: {
                    ...getAuthHeader(),
                },
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('로그인이 필요합니다.');
                }
                if (response.status === 403) {
                    throw new Error('접근 권한이 없습니다.');
                }
                if (response.status === 404) {
                    throw new Error('찜한 상품을 찾을 수 없습니다.');
                }
                const data = await response.json();
                throw new Error(data.message || '찜 삭제에 실패했습니다.');
            }

            return true;
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('네트워크 연결을 확인해주세요.');
            }
            console.error('deleteWishlist API Error:', error);
            throw error;
        }
    },
};
