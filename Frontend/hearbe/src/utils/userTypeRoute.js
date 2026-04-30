const USER_TYPE_TO_MALL_ROUTE = {
    BLIND: '/B/mall',
    LOW_VISION: '/B/mall',
    GENERAL: '/C/mall',
};

export const normalizeUserType = (value) => {
    if (typeof value !== 'string') return '';
    return value.trim().toUpperCase();
};

export const resolveMallRouteByUserType = (userType, fallbackRoute = '/B/mall') => {
    const normalized = normalizeUserType(userType);
    return USER_TYPE_TO_MALL_ROUTE[normalized] || fallbackRoute;
};

export const extractUserTypeFromResponse = (response) => {
    return (
        response?.data?.userType
        || response?.data?.user_type
        || response?.userType
        || response?.user_type
        || ''
    );
};

export const resolveMallRouteFromAuthResponse = (response, fallbackRoute = '/B/mall') => {
    const userType = extractUserTypeFromResponse(response);
    return resolveMallRouteByUserType(userType, fallbackRoute);
};

export const resolveMallRouteFromStorage = (fallbackRoute = '/B/mall') => {
    if (typeof window === 'undefined') return fallbackRoute;
    const storedUserType = localStorage.getItem('userType') || localStorage.getItem('user_type') || '';
    return resolveMallRouteByUserType(storedUserType, fallbackRoute);
};
