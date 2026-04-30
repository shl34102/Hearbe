import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/authAPI';
import { resolveMallRouteFromStorage } from '../utils/userTypeRoute';

export function useAutoLogin({ fallbackRoute, savedIdKey, setId, setRememberLogin, setIsLoading }) {
    const navigate = useNavigate();

    useEffect(() => {
        const run = async () => {
            const accessToken = localStorage.getItem('accessToken');
            const refreshToken = localStorage.getItem('refreshToken');

            if (accessToken) {
                navigate(resolveMallRouteFromStorage(fallbackRoute));
                return;
            }
            if (refreshToken) {
                try {
                    setIsLoading(true);
                    await authAPI.refreshToken();
                    navigate(resolveMallRouteFromStorage(fallbackRoute));
                    return;
                } catch {
                    localStorage.removeItem('accessToken');
                    localStorage.removeItem('refreshToken');
                } finally {
                    setIsLoading(false);
                }
            }
            const savedId = localStorage.getItem(savedIdKey);
            if (savedId) {
                setId(savedId);
                setRememberLogin(true);
            }
        };
        run();
    }, [navigate]);
}
