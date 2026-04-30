const config = {
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
    DEFAULT_MALL_URL: 'https://m.shopping.naver.com/',
};

export default config;
export const { API_BASE_URL, DEFAULT_MALL_URL } = config;
