import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Store, LogOut, ShoppingCart } from 'lucide-react';
import logoA from '../../assets/logoA.png';
import { cartAPI } from '../../services/cartAPI';
import { authAPI } from '../../services/authAPI';
import './CartB.css';

const CartB = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const [cartData, setCartData] = useState({});
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const platformNames = {
        1: '쿠팡',
        2: '네이버',
        3: '11번가',
        4: 'SSG'
    };

    useEffect(() => {
        const fetchCartItems = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await cartAPI.getCart();

                const groupedData = {};
                if (response.cart_items) {
                    response.cart_items.forEach(item => {
                        const platformName = platformNames[item.platform_id] || `Platform ${item.platform_id}`;
                        if (!groupedData[platformName]) {
                            groupedData[platformName] = [];
                        }
                        groupedData[platformName].push({
                            id: item.cart_item_id,
                            image: item.img_url || 'https://via.placeholder.com/80',
                            name: item.name,
                            price: item.price,
                            quantity: item.quantity || 1,
                            url: item.url
                        });
                    });
                }
                setCartData(groupedData);
            } catch (err) {
                console.error('Failed to fetch cart items:', err);
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        };

        fetchCartItems();
    }, []);

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
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('savedLoginId_b');
            localStorage.removeItem('savedLoginPassword_b');
            localStorage.removeItem('userData');
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            localStorage.removeItem('user_name');
            navigate('/main');
        }
    };

    return (
        <div className="cart-container">
            <img
                src={logoA}
                alt="Logo"
                className="cart-logo-left cursor-pointer"
                onClick={() => navigate('/main')}
            />

            <div className="mypage-topbar">
                <h1 className="mypage-topbar-title">마이페이지</h1>
                <div className="mypage-topbar-actions">
                    <button className="topbar-action cursor-pointer" onClick={() => navigate('/B/mall')}>
                        <Store size={56} />
                        <span>쇼핑몰</span>
                    </button>
                    <button className="topbar-action cursor-pointer" onClick={handleLogout}>
                        <LogOut size={56} />
                        <span>로그아웃</span>
                    </button>
                </div>
            </div>

            <div className="cart-content">
                {/* Sidebar */}
                <aside className="cart-sidebar">
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

                <main className="cart-main">
                    <div className="content-card">
                        <h2 className="content-title">
                            <ShoppingCart size={64} color="#FFF064" />
                            장바구니
                        </h2>

                        {isLoading && <div className="empty-cart">장바구니를 불러오는 중입니다.</div>}
                        {!isLoading && error && (
                            <div className="empty-cart">{error}</div>
                        )}

                        {Object.entries(cartData).map(([mallName, items]) => {
                            const totalQuantity = items.reduce((sum, item) => sum + (item.quantity || 1), 0);
                            const totalPrice = items.reduce((sum, item) => sum + (item.price * (item.quantity || 1)), 0);

                            return items.length > 0 && (
                                <div key={mallName} className="cart-mall-section">
                                    <div className="cart-mall-header">
                                        <h3 className="cart-mall-name">{mallName}</h3>
                                    </div>

                                    <div className="cart-items-list">
                                        {items.map(item => (
                                            <div
                                                key={item.id}
                                                className="cart-item-wrapper"
                                                onClick={() => item.url && window.open(item.url, '_blank', 'noopener,noreferrer')}
                                                style={{ cursor: item.url ? 'pointer' : 'default' }}
                                            >
                                                <div className="cart-item">
                                                    <img src={item.image} alt={item.name} className="cart-item-image" />
                                                    <div className="cart-item-details">
                                                        <div className="cart-item-name">{item.name}</div>
                                                        <div className="cart-item-price">{item.price.toLocaleString()}원</div>
                                                    </div>
                                                    <div className="cart-item-quantity">
                                                        <span className="quantity-text">{item.quantity}개</span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Summary Box */}
                                    <div className="cart-mall-summary">
                                        <div className="summary-item">
                                            <span className="summary-label-a">총 담은 수량:</span>
                                            <span className="summary-value">{totalQuantity}개</span>
                                        </div>
                                        <div className="summary-item">
                                            <span className="summary-label-a">주문 예상 금액:</span>
                                            <span className="summary-value">{totalPrice.toLocaleString()}원</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}

                        {!isLoading && Object.values(cartData).every(items => items.length === 0) && (
                            <div className="empty-cart">
                                장바구니가 비어있습니다.
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

export default CartB;
