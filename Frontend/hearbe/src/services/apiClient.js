// API Base URL Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Flag to prevent infinite retry loops
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

/**
 * Enhanced fetch wrapper with automatic token refresh on 401 errors
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Response>} - Fetch response
 */
export const apiClient = async (url, options = {}) => {
    try {
        const response = await fetch(url, options);

        // If not 401, return response as-is
        if (response.status !== 401) {
            return response;
        }

        // 401 detected - attempt token refresh

        // If already refreshing, queue this request
        if (isRefreshing) {
            return new Promise((resolve, reject) => {
                failedQueue.push({ resolve, reject });
            }).then(token => {
                // Retry with new token
                const newOptions = {
                    ...options,
                    headers: {
                        ...options.headers,
                        'Authorization': `Bearer ${token}`
                    }
                };
                return fetch(url, newOptions);
            });
        }

        isRefreshing = true;

        try {
            // Import authAPI dynamically to avoid circular dependency
            const { authAPI } = await import('./authAPI.js');

            // Attempt to refresh token
            await authAPI.refreshToken();

            // Get new token
            const newToken = localStorage.getItem('accessToken');

            // Process queued requests
            processQueue(null, newToken);

            isRefreshing = false;

            // Retry original request with new token
            const newOptions = {
                ...options,
                headers: {
                    ...options.headers,
                    'Authorization': `Bearer ${newToken}`
                }
            };

            return fetch(url, newOptions);

        } catch (refreshError) {
            // Refresh failed - clear tokens and redirect to login
            processQueue(refreshError, null);
            isRefreshing = false;

            console.error('❌ Token refresh failed. Redirecting to login...');

            // Clear all tokens
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');

            // Redirect to login
            window.location.href = '/';

            throw refreshError;
        }

    } catch (error) {
        console.error('API Client Error:', error);
        throw error;
    }
};

export { API_BASE_URL };
