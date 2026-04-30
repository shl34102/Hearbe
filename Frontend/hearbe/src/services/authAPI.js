import { apiClient } from './apiClient.js';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const OCR_WELFARE_CARD_URL = import.meta.env.VITE_OCR_WELFARE_CARD_URL || 'http://localhost:8000/api/v1/ocr/welfare-card';

// API Service for Authentication
export const authAPI = {
    register: async (userData) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/regist`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData),
            });


            const text = await response.text();

            let data = {};
            if (text) { // 응답 본문이 있을 경우에만 JSON 파싱 시도
                try { // 백엔드는 201 Created와 함께 ApiResponse 객체를 반환합니다.
                    // data는 { code: 201, message: "회원가입 완료", data: userId } 형태
                    data = text ? JSON.parse(text) : {};
                } catch (e) {
                    throw new Error('서버 응답 형식이 올바르지 않습니다. 응답: ' + text);
                }
            }

            if (response.status === 201) { // 백엔드는 201 Created를 반환합니다.
                return { success: true, message: data.message || '회원가입이 완료되었습니다', data: data.data };
            } else { // 201이 아닌 모든 다른 상태 코드 (4xx, 5xx 또는 예상치 못한 2xx)는 실패로 처리
                throw new Error(data.message || `회원가입에 실패했습니다. (상태: ${response.status})`);
            }
        } catch (error) {
            throw error;
        }
    },

    // ID 중복 확인 API
    checkDuplicate: async (userId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/checkId`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username: userId }),
            });


            const data = await response.json();


            return data;
        } catch (error) {
            throw new Error(error.message || '아이디 중복 확인 중 네트워크 오류가 발생했습니다.'); // 에러를 다시 던짐
        }
    },

    ocrWelfareCard: async (file) => {
        try {
            const maxFileSize = 20 * 1024 * 1024;
            if (!file) {
                throw new Error('OCR에 사용할 이미지 파일이 없습니다.');
            }
            if (typeof file.size === 'number' && file.size > maxFileSize) {
                throw new Error('이미지 파일은 최대 20MB까지 업로드할 수 있습니다.');
            }

            const formData = new FormData();
            formData.append('file', file, file.name || 'welfare-card.jpg');

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 45000);

            let response;
            try {
                response = await fetch(OCR_WELFARE_CARD_URL, {
                    method: 'POST',
                    body: formData,
                    signal: controller.signal,
                });
            } finally {
                clearTimeout(timeoutId);
            }

            const text = await response.text();
            let payload = {};

            if (text) {
                try {
                    payload = JSON.parse(text);
                } catch (e) {
                    throw new Error('OCR 서버 응답 형식이 올바르지 않습니다.');
                }
            }

            if (!response.ok) {
                throw new Error(payload.message || payload.error || `OCR 인식에 실패했습니다. (상태: ${response.status})`);
            }

            const data = payload?.data && typeof payload.data === 'object' ? payload.data : payload;

            return {
                card_company: data?.card_company ?? null,
                card_number: data?.card_number ?? null,
                expiration_date: data?.expiration_date ?? null,
                cvc: data?.cvc ?? null,
                confidence: {
                    card_company: data?.confidence?.card_company ?? null,
                    card_number: data?.confidence?.card_number ?? null,
                    expiration_date: data?.confidence?.expiration_date ?? null,
                    cvc: data?.confidence?.cvc ?? null,
                },
                raw_text: Array.isArray(data?.raw_text) ? data.raw_text : [],
            };
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('OCR 요청 시간이 초과되었습니다. (약 45초)');
            }
            console.error('OCR Welfare Card API Error:', error);
            throw error;
        }
    },

    login: async (id, password) => {
        try {
            if (typeof id !== 'string' || typeof password !== 'string') {
                throw new Error('로그인 값이 올바르지 않습니다.');
            }
            const username = id.trim();
            const resolvedPassword = password;

            if (!username || !resolvedPassword) {
                throw new Error('로그인 값이 올바르지 않습니다.');
            }

            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password: resolvedPassword }),
            });

            const text = await response.text();

            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                throw new Error('서버 응답 형식이 올바르지 않습니다.');
            }

            if (!response.ok) {
                const error = new Error(data.message || '로그인에 실패했습니다.');
                error.status = response.status;
                throw error;
            }

            if (data.data && data.data.accessToken) {
                localStorage.setItem('accessToken', data.data.accessToken);
            }
            // refreshToken 저장 (토큰 갱신을 위해 필수)
            if (data.data && data.data.refreshToken) {
                localStorage.setItem('refreshToken', data.data.refreshToken);
            }
            // user_id 저장
            if (data.data && data.data.id) {
                localStorage.setItem('user_id', data.data.id);
                localStorage.setItem('username', username);
            }
            if (data.data && data.data.name) {
                localStorage.setItem('user_name', data.data.name);
            }
            // userType 저장 (BLIND, LOW_VISION, GENERAL)
            const resolvedUserType = data?.data?.userType || data?.data?.user_type || data?.userType || data?.user_type;
            if (resolvedUserType) {
                localStorage.setItem('userType', String(resolvedUserType).trim().toUpperCase());
            }

            return data;
        } catch (error) {
            console.error('Login API Error:', error);
            throw error;
        }
    },

    getUserProfile: async () => {
        try {
            const token = localStorage.getItem('accessToken');

            if (!token) {
                throw new Error('로그인이 필요합니다');
            }

            const response = await apiClient(`${API_BASE_URL}/auth/mypage`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('로그인이 필요합니다');
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
            console.error('getUserProfile API Error:', error);
            throw error;
        }
    },
    sendEmailVerification: async (email, username = null, name = null) => {
        try {
            const body = { email };
            if (username) body.username = username;
            if (name) body.name = name;

            const response = await fetch(`${API_BASE_URL}/auth/email/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '인증번호 발송 실패');
            return data;
        } catch (error) {
            console.error('Send Email Verification Error:', error);
            throw error;
        }
    },

    resetPassword: async (email, newPassword) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/resetPassword`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, newPassword }),
            });

            const data = await response.json();

            if (!response.ok) throw new Error(data.message || '비밀번호 재설정 실패');
            return data;
        } catch (error) {
            console.error('Reset Password API Error:', error);
            throw error;
        }
    },

    verifyEmailCode: async (email, code) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/email/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, code }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '인증번호 확인 실패');
            return data;
        } catch (error) {
            console.error('Verify Email Code Error:', error);
            throw error;
        }
    },

    findId: async (name, email) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/findIdByEmail`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '아이디 찾기 실패');
            return data;
        } catch (error) {
            console.error('Find ID API Error:', error);
            throw error;
        }
    },

    refreshToken: async () => {
        try {
            const refreshToken = localStorage.getItem('refreshToken');
            if (!refreshToken) {
                throw new Error('로그인 정보가 만료되었습니다. 다시 로그인해주세요.');
            }


            const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refreshToken }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || '토큰 갱신에 실패했습니다.');
            }

            if (data.data && data.data.accessToken) {
                localStorage.setItem('accessToken', data.data.accessToken);
            }
            if (data.data && data.data.refreshToken) {
                localStorage.setItem('refreshToken', data.data.refreshToken);
            }

            return data;
        } catch (error) {
            console.error('RefreshToken API Error:', error);
            throw error;
        }
    },

    logout: async () => {
        try {
            const token = localStorage.getItem('accessToken');

            if (!token) {
                return { success: true };
            }

            const response = await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                }
            });

            if (response.status === 204) {
                return { success: true };
            }

            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('JSON parse error:', e);
                throw new Error('서버 응답 형식이 올바르지 않습니다.');
            }

            if (!response.ok) {
                throw new Error(data.message || '로그아웃에 실패했습니다.');
            }

            return data;
        } catch (error) {
            console.error('Logout API Error:', error);
            throw error;
        } finally {
            // localStorage 정리
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('savedLoginId_b');
            localStorage.removeItem('savedLoginId_c');
            localStorage.removeItem('savedLoginPassword_b');
            localStorage.removeItem('savedLoginPassword_c');
            localStorage.removeItem('userData');
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            localStorage.removeItem('user_name');
            localStorage.removeItem('userType');

            // sessionStorage 정리
            sessionStorage.clear();
        }
    },

    deleteAccount: async (password) => {
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${API_BASE_URL}/auth/delete-account`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || '회원탈퇴에 실패했습니다.');
            }

            return data;
        } catch (error) {
            console.error('Delete Account API Error:', error);
            throw error;
        }
    }
    ,
    findIdByWelfareCard: async (welfareCard) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/findId`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ welfare_card: welfareCard }),
            });

            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('JSON parse error:', e);
                throw new Error('서버 응답 형식이 올바르지 않습니다.');
            }

            if (!response.ok) {
                // 서버 검증 에러 시 상세 필드 에러 메시지 추출
                if (data.data && typeof data.data === 'object') {
                    const fieldErrors = Object.values(data.data).join('\n');
                    if (fieldErrors) {
                        throw new Error(fieldErrors);
                    }
                }
                throw new Error(data.message || '아이디 찾기에 실패했습니다.');
            }

            return data;
        } catch (error) {
            console.error('Find ID By Welfare Card API Error:', error);
            throw error;
        }
    }
    ,
    resetPasswordBlind: async (welfareCard, newPassword) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/resetPasswordBlind`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    welfare_card: welfareCard,
                    new_password: newPassword
                }),
            });

            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('JSON parse error:', e);
                throw new Error('서버 응답 형식이 올바르지 않습니다.');
            }

            if (!response.ok) {
                throw new Error(data.message || '비밀번호 변경에 실패했습니다.');
            }

            return data;
        } catch (error) {
            console.error('Reset Password Blind API Error:', error);
            throw error;
        }
    },
    getWelfareCard: async () => {
        try {
            const token = localStorage.getItem('accessToken');
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/welfare`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });

            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('JSON parse error:', e);
                throw new Error('서버 응답 형식이 올바르지 않습니다.');
            }

            if (!response.ok) {
                throw new Error(data.message || '복지카드 조회에 실패했습니다.');
            }

            return data;
        } catch (error) {
            console.error('Get Welfare Card API Error:', error);
            throw error;
        }
    },
    updateWelfareCard: async (welfareCard) => {
        try {
            const token = localStorage.getItem('accessToken');
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }

            const response = await apiClient(`${API_BASE_URL}/welfare`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(welfareCard),
            });

            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('JSON parse error:', e);
                throw new Error('서버 응답 형식이 올바르지 않습니다.');
            }

            if (!response.ok) {
                throw new Error(data.message || '복지카드 저장에 실패했습니다.');
            }

            return data;
        } catch (error) {
            console.error('Update Welfare Card API Error:', error);
            throw error;
        }
    },
    verifyWelfareCard: async (welfareCard) => {
        try {
            const response = await fetch(`${API_BASE_URL}/welfare/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(welfareCard),
            });

            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('JSON parse error:', e);
                throw new Error('서버 응답 형식이 올바르지 않습니다.');
            }

            if (!response.ok) {
                throw new Error(data.message || '복지카드 인증에 실패했습니다.');
            }

            return data;
        } catch (error) {
            console.error('Verify Welfare Card API Error:', error);
            throw error;
        }
    }
};

if (import.meta.env.DEV) {
    window.authAPI = authAPI;

    window.testTokenRefresh = () => {

        // 1. authAPI 로드 확인

        // 2. refreshToken 존재 확인
        const hasRefreshToken = !!localStorage.getItem('refreshToken');

        if (!hasRefreshToken) {
            console.error('❌ RefreshToken이 없습니다. 먼저 로그인해주세요.');
            return;
        }

        // 3. 현재 토큰 저장
        const oldAccessToken = localStorage.getItem('accessToken');
        const oldRefreshToken = localStorage.getItem('refreshToken');

        // 4. 토큰 갱신 실행
        return authAPI.refreshToken()
            .then(result => {

                const newAccessToken = localStorage.getItem('accessToken');
                const newRefreshToken = localStorage.getItem('refreshToken');


                return result;
            })
            .catch(error => {
                console.error('❌ 갱신 실패:', error.message);
                throw error;
            });
    };

}
