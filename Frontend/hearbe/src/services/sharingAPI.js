import axios from 'axios';
import { API_BASE_URL } from '../config';

const API_PATH = `${API_BASE_URL}/api/sharing`;

export const sharingAPI = {
    // 세션 시작
    startSession: async (sessionData) => {
        // sessionData: { hostUserId: number, meetingCode: string }
        const token = localStorage.getItem('accessToken');
        try {
            const response = await axios.post(`${API_PATH}/start`, sessionData, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return response.data;
        } catch (error) {
            console.error("Start session failed", error);
            throw error;
        }
    },

    // 세션 종료
    endSession: async (sessionId) => {
        const token = localStorage.getItem('accessToken');
        try {
            const response = await axios.post(`${API_PATH}/end/${sessionId}`, {}, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return response.data;
        } catch (error) {
            console.error("End session failed", error);
            throw error;
        }
    }
};
