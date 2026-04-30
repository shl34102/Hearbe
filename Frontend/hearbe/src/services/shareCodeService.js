import axios from 'axios';

// Backend API URL (configured in Vite proxy or absolute URL)
// Assuming proxy is set up in vite.config.js to forward /api to backend
const API_BASE_URL = '/api/share';

export const shareCodeService = {
    /**
     * 공유 코드 생성 (A형)
     * @returns {Promise<string>} 4자리 공유 코드
     */
    createCode: async () => {
        try {
            const response = await axios.post(`${API_BASE_URL}/code`);
            // Response format: { code: "1234" }
            return response.data.code;
        } catch (error) {
            console.error('Failed to create share code:', error);
            throw error;
        }
    },

    /**
     * 공유 코드 검증 (S형)
     * @param {string} code 
     * @returns {Promise<boolean>} 유효 여부
     */
    validateCode: async (code) => {
        try {
            const response = await axios.get(`${API_BASE_URL}/code/${code}`);
            // Response format: { valid: true, message: "..." }
            return response.data.valid;
        } catch (error) {
            console.error('Share code validation failed:', error);
            return false;
        }
    }
};
