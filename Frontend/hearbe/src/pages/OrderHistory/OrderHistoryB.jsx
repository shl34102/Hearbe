import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, LogOut, Package } from 'lucide-react';
import logoA from '../../assets/logoA.png';
import { orderAPI } from '../../services/orderAPI';
import { authAPI } from '../../services/authAPI';
import './OrderHistoryB.css';

const OrderHistoryB = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const [orderData, setOrderData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);


    // Platform ID to name mapping
    const platformNames = {
        1: '쿠팡',
        2: '네이버',
        3: '11번가',
        4: 'SSG',
        5: 'G마켓',
        6: '컬리'
    };

    const resolvePlatformName = (order) => {
        return (
            platformNames[order.platform_id] ||
            order.platform_name ||
            order.platformName ||
            order.mall_name ||
            order.mallName ||
            (order.platform_id ? `플랫폼 ${order.platform_id}` : '기타 쇼핑몰')
        );
    };

    const formatOrderDate = (orderedAt) => {
        if (!orderedAt) return '날짜 미상';
        if (orderedAt.includes('T')) return orderedAt.split('T')[0];
        if (orderedAt.includes(' ')) return orderedAt.split(' ')[0];
        return orderedAt;
    };

    const menuItems = [
        { id: 'profile', label: '회원 정보', path: '/B/member-info' },
        { id: 'orders', label: '주문 내역', path: '/B/order-history' },
        { id: 'wishlist', label: '찜한 상품', path: '/B/wishlist' },
        { id: 'cart', label: '장바구니', path: '/B/cart' },
        { id: 'card', label: <>장애인 복지<br />카드 변경</>, path: '/B/card-management' }
    ];

    const currentPath = location.pathname;

    const handleLogout = async () => {
        try {
            await authAPI.logout();
        } catch (err) {
            console.warn('Logout failed:', err);
        } finally {
            localStorage.removeItem('accessToken');
            localStorage.removeItem('userData');
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            navigate('/main');
        }
    };

    // API 호출
    useEffect(() => {
        const fetchOrders = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await orderAPI.getOrders();

                if (response.data && response.data.orders) {
                    const ordersByDate = {};
                    response.data.orders.forEach(order => {
                        const dateKey = formatOrderDate(order.ordered_at);
                        const mallName = resolvePlatformName(order);

                        if (!ordersByDate[dateKey]) {
                            ordersByDate[dateKey] = {
                                date: dateKey,
                                platforms: {}
                            };
                        }

                        if (!ordersByDate[dateKey].platforms[mallName]) {
                            ordersByDate[dateKey].platforms[mallName] = {
                                mall: mallName,
                                orderUrls: [],
                                items: []
                            };
                        }

                        if (order.order_url) {
                            ordersByDate[dateKey].platforms[mallName].orderUrls.push(order.order_url);
                        }

                        if (order.items && order.items.length > 0) {
                            order.items.forEach(item => {
                                ordersByDate[dateKey].platforms[mallName].items.push({
                                    id: `${order.order_id}-${item.name}-${item.url || ''}`,
                                    name: item.name,
                                    price: item.price,
                                    quantity: item.quantity || 1,
                                    imgUrl: item.img_url,
                                    productUrl: item.url,
                                    deliverUrl: item.deliver_url
                                });
                            });
                        }
                    });

                    // Convert to sorted array
                    const sortedGroups = Object.values(ordersByDate).map(dateGroup => ({
                        date: dateGroup.date,
                        platformGroups: Object.values(dateGroup.platforms)
                    })).sort((a, b) => {
                        if (a.date === '날짜 미상') return 1;
                        if (b.date === '날짜 미상') return -1;
                        return new Date(b.date) - new Date(a.date);
                    });

                    setOrderData(sortedGroups);
                }
            } catch (err) {
                console.error('Failed to fetch orders:', err);
                setError(err.message);

                // 401 에러 시 로그인 페이지로 이동
                if (err.message === '로그인이 필요합니다.') {
                    navigate('/B/login');
                }
            } finally {
                setIsLoading(false);
            }
        };

        fetchOrders();
    }, [navigate]);

    const handleRetry = () => {
        window.location.reload();
    };

    const formatDate = (datetime) => {
        if (!datetime) return '날짜 미상';
        const date = new Date(datetime);
        if (isNaN(date.getTime())) return datetime;
        return date.toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    };

    const handleOrderDetail = (orderUrl) => {
        if (orderUrl) {
            window.open(orderUrl, '_blank', 'noopener,noreferrer');
        }
    };

    const handleTrackDelivery = (deliverUrl) => {
        if (deliverUrl) {
            window.open(deliverUrl, '_blank', 'noopener,noreferrer');
        }
    };


    return (
        <div className="orderhistory-container">
            <img
                src={logoA}
                alt="Logo"
                className="orderhistory-logo-left cursor-pointer"
                onClick={() => navigate('/main')}
            />

            <div className="mypage-topbar">
                <h1 className="mypage-topbar-title">마이페이지</h1>
                <div className="mypage-topbar-actions">
                    <button className="topbar-action cursor-pointer" onClick={() => navigate('/B/mall')}>
                        <Home size={56} />
                        <span>홈</span>
                    </button>
                    <button className="topbar-action cursor-pointer" onClick={handleLogout}>
                        <LogOut size={56} />
                        <span>로그아웃</span>
                    </button>
                </div>
            </div>

            <div className="orderhistory-content">
                {/* Sidebar */}
                <aside className="orderhistory-sidebar">
                    <div className="sidebar-menu-card">
                        <nav className="sidebar-nav">
                            {menuItems.map(item => (
                                <button
                                    key={item.id}
                                    className={`sidebar-item cursor-pointer ${currentPath === item.path ? 'active' : ''}`}
                                    onClick={() => navigate(item.path)}
                                >
                                    {item.label}
                                </button>
                            ))}
                        </nav>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="orderhistory-main">
                    <div className="content-card">
                        <h2 className="content-title">
                            <Package size={64} color="#FFF064" />
                            주문 내역
                        </h2>

                        {/* 로딩 상태 */}
                        {isLoading && (
                            <div className="loading-state">
                                <div className="spinner"></div>
                                <p>주문 내역을 불러오는 중...</p>
                            </div>
                        )}

                        {/* 에러 상태 */}
                        {!isLoading && error && (
                            <div className="error-state">
                                <p className="error-message">주문 내역을 불러오지 못했습니다.</p>
                                <p className="error-detail">{error}</p>
                                <button className="retry-btn cursor-pointer" onClick={handleRetry}>
                                    다시 시도
                                </button>
                            </div>
                        )}

                        {/* 빈 상태 */}
                        {!isLoading && !error && orderData.length === 0 && (
                            <div className="empty-orders">
                                주문 내역이 없습니다.
                            </div>
                        )}

                        {/* 주문 내역 데이터 */}
                        {!isLoading && !error && orderData.length > 0 && (
                            <div className="orders-container">
                                {orderData.map((dateGroup, dateIdx) => (
                                    <div key={dateIdx} className="date-group-a">
                                        {/* Date Header */}
                                        <div className="date-header-main-a">
                                            <div className="date-indicator-a"></div>
                                            <h2 className="date-title-a">{dateGroup.date}</h2>
                                        </div>

                                        {/* Platform Sections within this date */}
                                        {dateGroup.platformGroups.map((platformGroup, platformIdx) => {
                                            const detailUrl = platformGroup.orderUrls && platformGroup.orderUrls.length > 0 ? platformGroup.orderUrls[0] : '';
                                            return (
                                                <div key={platformIdx} className="platform-section-a">
                                                    <div className="platform-header-a">
                                                        <h3 className="platform-name-a">{platformGroup.mall}</h3>
                                                        <button
                                                            className="btn-order-detail cursor-pointer"
                                                            onClick={() => detailUrl && window.open(detailUrl, '_blank')}
                                                            disabled={!detailUrl}
                                                        >
                                                            주문 상세 조회
                                                        </button>
                                                    </div>
                                                    <div className="order-items-list">
                                                        {platformGroup.items.map((item) => (
                                                            <div key={item.id} className="order-item-card">
                                                                <div className="item-image">
                                                                    {item.imgUrl ? (
                                                                        <img src={item.imgUrl} alt={item.name} />
                                                                    ) : (
                                                                        <div className="item-placeholder">📦</div>
                                                                    )}
                                                                </div>
                                                                <div className="item-info">
                                                                    <div className="item-name">{item.name}</div>
                                                                    <div className="item-price-a">{item.price.toLocaleString()}원</div>
                                                                </div>
                                                                <div className="item-quantity">{item.quantity}개</div>
                                                                <div className="item-actions">
                                                                    <button
                                                                        className="btn-product-detail cursor-pointer"
                                                                        onClick={() => item.productUrl && window.open(item.productUrl, '_blank')}
                                                                        disabled={!item.productUrl}
                                                                    >
                                                                        상품 조회
                                                                    </button>
                                                                    <button
                                                                        className="btn-delivery-track cursor-pointer"
                                                                        onClick={() => item.deliverUrl && window.open(item.deliverUrl, '_blank')}
                                                                        disabled={!item.deliverUrl}
                                                                    >
                                                                        배송 조회
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </main>
            </div>

            <footer className="landing-footer-a">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default OrderHistoryB;









