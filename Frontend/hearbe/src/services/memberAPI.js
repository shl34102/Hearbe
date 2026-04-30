// 회원 API
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

// Member API Service
export const memberAPI = {
    /**
     * 회원 프로필 조회
     * GET /members/profile
     * @returns {Promise<Object>} 회원 프로필 데이터
     */
    getProfile: async () => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/members/profile`, {
                method: 'GET',
                headers: {
                    ...getAuthHeader(),
                    'Content-Type': 'application/json'
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
                    throw new Error('회원정보를 찾을 수 없습니다.');
                }
                if (response.status >= 500) {
                    throw new Error('서버 오류가 발생했습니다.');
                }
                throw new Error('요청이 실패했습니다.');
            }

            return await response.json();
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('네트워크 연결을 확인해주세요.');
            }
            console.error('getProfile API Error:', error);
            throw error;
        }
    },

    /**
     * 회원 프로필 수정
     * PUT /members/profile
     * @param {Object} profileData - 수정할 프로필 데이터
     * @returns {Promise<Object>} 수정된 프로필 데이터
     */
    updateProfile: async (profileData) => {
        try {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/members/profile`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader(),
                },
                body: JSON.stringify(profileData),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('로그인이 필요합니다.');
                }
                if (response.status === 403) {
                    throw new Error('접근 권한이 없습니다.');
                }
                if (response.status === 404) {
                    throw new Error('회원정보를 찾을 수 없습니다.');
                }
                if (response.status >= 500) {
                    throw new Error('서버 오류가 발생했습니다.');
                }
                throw new Error('요청이 실패했습니다.');
            }

            return await response.json();
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('네트워크 연결을 확인해주세요.');
            }
            console.error('updateProfile API Error:', error);
            throw error;
        }
    },
};
