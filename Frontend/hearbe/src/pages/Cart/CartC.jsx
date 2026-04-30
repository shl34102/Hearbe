import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingCart, Store, User, LogOut } from 'lucide-react';
import { cartAPI } from '../../services/cartAPI';
import { authAPI } from '../../services/authAPI';
import Swal from 'sweetalert2';
import '../MyPage/mypage-common.css';
import './CartC.css';
import logoC from '../../assets/logoC.png';

const CartC = ({ isEmbedded = false }) => {
    const navigate = useNavigate();
    const [cartItems, setCartItems] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const [userData, setUserData] = useState({
        name: '',
        email: '',
    });

    // localStorage에서 사용자 정보 로드
    useEffect(() => {
        const userName = localStorage.getItem('user_name');
        setUserData({
            name: userName || '회원',
            email: '',
        });
    }, []);

    const sidebarItems = [
        { id: 'member-info', label: '회원 정보', path: '/C/member-info' },
        { id: 'order-history', label: '주문 내역', path: '/C/order-history' },
        { id: 'wishlist', label: '찜한 상품', path: '/C/wishlist' },
        { id: 'cart', label: '장바구니', path: '/C/cart' },
    ];

    // Platform ID to name mapping (A형과 동일)
    const platformNames = {
        1: '쿠팡',
        2: '네이버',
        3: '11번가',
        4: 'SSG'
    };

    // Fetch cart items on mount
    useEffect(() => {
        const fetchCartItems = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await cartAPI.getCart();

                // 1. 응답 처리
                let itemsList = [];
                if (Array.isArray(response)) {
                    itemsList = response;
                } else if (response.data && Array.isArray(response.data.items)) {
                    itemsList = response.data.items;
                } else if (response.data && Array.isArray(response.data)) {
                    itemsList = response.data;
                } else if (response.items && Array.isArray(response.items)) {
                    itemsList = response.items;
                } else if (response.cartItems && Array.isArray(response.cartItems)) {
                    itemsList = response.cartItems;
                } else if (response.cart_items && Array.isArray(response.cart_items)) {
                    itemsList = response.cart_items;
                } else if (response.cart && Array.isArray(response.cart)) {
                    itemsList = response.cart;
                }


                // 2. 데이터 변환
                if (itemsList.length > 0) {
                    const transformedItems = itemsList.map((item, index) => ({
                        id: item.id || item.cart_item_id || item.cartId || item.cart_id || index,
                        name: item.name || item.product_name || item.productName || '상품명 없음',
                        price: item.price || 0,
                        quantity: item.quantity || 1,
                        image: item.img_url || item.imgUrl || item.image || item.thumbnail || '📦',
                        mallName: platformNames[item.platform_id] || item.platform_name || item.platformName || item.mall_name || '기타 쇼핑몰',
                    }));
                    setCartItems(transformedItems);
                } else {
                    setCartItems([]);
                }
            } catch (err) {
                console.error('Failed to fetch cart items:', err);
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        };

        fetchCartItems();
    }, []);

    const groupedItems = cartItems.reduce((acc, item) => {
        if (!acc[item.mallName]) acc[item.mallName] = [];
        acc[item.mallName].push(item);
        return acc;
    }, {});

    const handleRemoveItem = async (id) => {
        try {
            await cartAPI.deleteCart(id);
            setCartItems(items => items.filter(item => item.id !== id));
        } catch (err) {
            console.error('Failed to delete cart item:', err);
            Swal.fire({
                icon: 'error',
                text: err.message || '상품 삭제에 실패했습니다.',
                confirmButtonText: '확인',
                confirmButtonColor: '#7c3aed'
            });
        }
    };

    const totalPrice = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const totalItems = cartItems.reduce((sum, item) => sum + item.quantity, 0);

    const handleLogout = async () => {
        try {
            await authAPI.logout();
            navigate('/main');
        } catch (error) {
            console.error('Logout failed:', error);
            localStorage.removeItem('accessToken');
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            navigate('/main');
        }
    };

    if (isEmbedded) {
        return (
            <div className="cart-page-container" style={{
                position: 'static',
                width: '100%',
                minHeight: 'auto',
                background: 'transparent',
                padding: 0,
                margin: 0
            }}>
                <main className="cart-content" style={{ padding: 0 }}>
                    <div className="cart-list-wrapper" style={{ marginBottom: 0 }}>
                        {isLoading ? (
                            <div className="empty-cart">
                                <p>장바구니를 불러오는 중...</p>
                            </div>
                        ) : error ? (
                            <div className="empty-cart">
                                <p style={{ color: '#e53e3e' }}>{error}</p>
                            </div>
                        ) : cartItems.length === 0 ? (
                            <div className="empty-cart">
                                <ShoppingCart className="empty-icon" />
                                <p>장바구니가 비어있습니다</p>
                            </div>
                        ) : (
                            Object.entries(groupedItems).map(([mallName, items]) => {
                                const mallTotalPrice = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
                                const mallTotalItems = items.reduce((sum, item) => sum + item.quantity, 0);

                                return (
                                    <section key={mallName} className="mall-group">
                                        <div className="cart-mall-name-header">
                                            <div className="mall-indicator" />
                                            <h2>{mallName}</h2>
                                        </div>

                                        <div className="item-grid">
                                            {items.map(item => (
                                                <div key={item.id} className="cart-item-card">
                                                    <div className="item-image-box">
                                                        {item.image && item.image.startsWith('http') ? (
                                                            <img src={item.image} alt={item.name} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '1rem' }} />
                                                        ) : (
                                                            item.image || '📦'
                                                        )}
                                                    </div>
                                                    <div className="item-info">
                                                        <h3>{item.name}</h3>
                                                        <p className="item-price">{item.price.toLocaleString()}원</p>
                                                    </div>
                                                    <div className="item-quantity-badge-right">
                                                        <span className="count">{item.quantity}개</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        <div className="mall-footer">
                                            <div className="mall-summary-detail">
                                                <div className="summary-row">
                                                    <span className="summary-label">총 담은 수량 :</span>
                                                    <span className="summary-value">{mallTotalItems}개</span>
                                                </div>
                                                <div className="summary-row highlight">
                                                    <span className="summary-label">주문 예상 금액 :</span>
                                                    <span className="summary-value price">{mallTotalPrice.toLocaleString()} 원</span>
                                                </div>
                                            </div>

                                        </div>
                                    </section>
                                );
                            })
                        )}
                    </div>
                </main>
            </div>
        );
    }

    return (
        <div className="mypage-container">
            {/* Header */}
            <header className="mall-header-c">
                <div className="header-left-c">
                    <div className="title-area-c" style={{ marginLeft: 0, cursor: 'pointer' }} onClick={() => navigate('/main')}>
                        <img src={logoC} alt="HearBe Logo" style={{ height: '70px', objectFit: 'contain' }} />
                    </div>
                </div>

                <div className="header-right-c">
                    <button className="nav-item-c cursor-pointer" onClick={() => navigate('/C/mall')}>
                        <div className="nav-icon-c"><Store size={24} /></div>
                        <span>쇼핑몰</span>
                    </button>
                    <button className="nav-item-c cursor-pointer" onClick={handleLogout}>
                        <div className="nav-icon-c"><LogOut size={24} /></div>
                        <span>로그아웃</span>
                    </button>
                </div>
            </header>

            <div className="mypage-layout">
                {/* Sidebar */}
                <aside className="mypage-sidebar">
                    <div className="sidebar-profile-card">
                        <div className="sidebar-avatar">
                            <User size={40} color="#7c3aed" />
                        </div>
                        <div className="sidebar-profile-info">
                            <h2 className="sidebar-name">{userData.name}님</h2>
                            <span className="sidebar-badge">hearbe 회원</span>
                        </div>
                        <p className="sidebar-welcome">오늘도 즐거운 쇼핑 되세요!</p>
                    </div>

                    <div className="sidebar-menu-list">
                        {sidebarItems.map((item) => (
                            <button
                                key={item.id}
                                onClick={() => navigate(item.path)}
                                className={`mp-sidebar-item cursor-pointer ${item.id === 'cart' ? 'active' : ''}`}
                            >
                                <span className="label">{item.label}</span>
                            </button>
                        ))}
                    </div>
                </aside>

                {/* Main Content */}
                <main className="mypage-content">
                    <section className="dashboard-card full-height">
                        <div className="cart-content-title-row">
                            <div className="cart-content-title-icon">
                                <ShoppingCart size={28} />
                            </div>
                            <h2 className="card-title-lg" style={{ marginBottom: 0 }}>장바구니</h2>
                        </div>
                        <div className="cart-content-body">
                            {isLoading ? (
                                <div className="cart-status-message">
                                    장바구니를 불러오는 중...
                                </div>
                            ) : error ? (
                                <div className="cart-status-message cart-error">
                                    {error}
                                </div>
                            ) : cartItems.length === 0 ? (
                                <div className="cart-status-message">
                                    장바구니에 담긴 상품이 없습니다.
                                </div>
                            ) : (
                                Object.entries(groupedItems).map(([mallName, items]) => {
                                    const mallTotalPrice = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
                                    const mallTotalItems = items.reduce((sum, item) => sum + item.quantity, 0);

                                    return (
                                        <section key={mallName} className="mall-group">
                                            <div className="cart-mall-name-header">
                                                <div className="mall-indicator" />
                                                <h2>{mallName}</h2>
                                            </div>

                                            <div className="item-grid">
                                                {items.map(item => (
                                                    <div key={item.id} className="cart-item-card">
                                                        <div className="item-image-box">
                                                            {item.image && item.image.startsWith('http') ? (
                                                                <img src={item.image} alt={item.name} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '1rem' }} />
                                                            ) : (
                                                                item.image || '📦'
                                                            )}
                                                        </div>
                                                        <div className="item-info">
                                                            <h3>{item.name}</h3>
                                                            <p className="item-price">{item.price.toLocaleString()}원</p>
                                                        </div>
                                                        <div className="item-quantity-badge-right">
                                                            <span className="count">{item.quantity}개</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>

                                            <div className="mall-footer">
                                                <div className="mall-summary-detail">
                                                    <div className="summary-row">
                                                        <span className="summary-label">총 담은 수량 :</span>
                                                        <span className="summary-value">{mallTotalItems}개</span>
                                                    </div>
                                                    <div className="summary-row highlight">
                                                        <span className="summary-label">주문 예상 금액 :</span>
                                                        <span className="summary-value price">{mallTotalPrice.toLocaleString()} 원</span>
                                                    </div>
                                                </div>

                                            </div>
                                        </section>
                                    );
                                })
                            )}
                        </div>
                    </section>
                </main>
            </div>

            <footer className="landing-footer">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default CartC;
