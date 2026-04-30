import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Store, LogOut, Heart } from 'lucide-react';
import logoA from '../../assets/logoA.png';
import { wishlistAPI } from '../../services/wishlistAPI';
import { cartAPI } from '../../services/cartAPI';
import { authAPI } from '../../services/authAPI';
import './WishlistB.css';

const WishlistB = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const [wishlistData, setWishlistData] = useState({});
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);


    const platformDisplayNames = {
        'coupang': '쿠팡',
        'naver': '네이버',
        '11st': '11번가',
        'ssg': 'SSG',
        'gmarket': 'G마켓'
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
        fetchWishlist();
    }, []);

    const fetchWishlist = async () => {
        try {
            setIsLoading(true);
            setError(null);
            const response = await wishlistAPI.getWishlist();

            const groupedData = {};

            if (response.items && response.items.length > 0) {
                response.items.forEach(item => {
                    const platformKey = (item.platform_name || '').toLowerCase();
                    const platform = platformDisplayNames[platformKey] || item.platform_name;

                    if (!groupedData[platform]) {
                        groupedData[platform] = [];
                    }

                    groupedData[platform].push({
                        id: item.wishlist_item_id,
                        image: item.img_url || 'https://via.placeholder.com/150',
                        date: item.created_at ? item.created_at.split('T')[0].replace(/-/g, '.') : '',
                        name: item.product_name,
                        price: item.price ? `${item.price.toLocaleString()}원` : '',
                        url: item.product_url,
                        liked: item.liked
                    });
                });
            }

            setWishlistData(groupedData);
        } catch (err) {
            console.error('Failed to fetch wishlist:', err);
            setError(err.message);

            // 401 에러 시 로그인 페이지로 이동
            if (err.message === '로그인이 필요합니다.') {
                navigate('/B/login');
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleAddToCart = async (item) => {
        try {
            await cartAPI.addCart({
                productUrl: item.url,
                productName: item.name,
                imgUrl: item.image
            });
            Swal.fire({
                icon: 'success',
                text: `${item.name}을(를) 장바구니에 담았습니다.`,
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        } catch (err) {
            console.error('Failed to add to cart:', err);
            Swal.fire({
                icon: 'error',
                text: err.message || '장바구니 담기에 실패했습니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    const handleRetry = () => {
        fetchWishlist();
    };

    return (
        <div className="wishlist-container">
            <img
                src={logoA}
                alt="Logo"
                className="wishlist-logo-left cursor-pointer"
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

            <div className="wishlist-content">
                {/* Sidebar */}
                <aside className="wishlist-sidebar">
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
                <main className="wishlist-main">
                    <div className="content-card">
                        <h2 className="content-title">
                            <Heart size={64} color="#FFF064" fill="#FFF064" />
                            찜한 상품
                        </h2>

                        {/* 로딩 상태 */}
                        {isLoading && (
                            <div className="loading-state">
                                <div className="spinner"></div>
                                <p>찜한 상품을 불러오는 중...</p>
                            </div>
                        )}

                        {/* 에러 상태 */}
                        {!isLoading && error && (
                            <div className="error-state">
                                <p className="error-message">찜한 상품을 불러오지 못했습니다.</p>
                                <p className="error-detail">{error}</p>
                                <button className="retry-btn cursor-pointer" onClick={handleRetry}>
                                    다시 시도
                                </button>
                            </div>
                        )}

                        {/* 빈 상태 */}
                        {!isLoading && !error && Object.keys(wishlistData).length === 0 ? (
                            <div className="empty-wishlist">
                                찜한 상품이 없습니다.
                            </div>
                        ) : (
                            <>
                                {/* Wishlist by Mall */}
                                {Object.entries(wishlistData).map(([mallName, items]) => (
                                    items.length > 0 && (
                                        <div key={mallName} className="mall-section">
                                            <div className="mall-header">
                                                <h3 className="mall-name">{mallName}</h3>
                                            </div>

                                            <div className="items-list">
                                                {items.map(item => (
                                                    <div
                                                        key={item.id}
                                                        className="wishlist-item-wrapper cursor-pointer"
                                                        onClick={() => item.url && window.open(item.url, '_blank', 'noopener,noreferrer')}
                                                        style={{ cursor: item.url ? 'pointer' : 'default' }}
                                                    >
                                                        <div className="wishlist-item">
                                                            <img src={item.image} alt={item.name} className="item-image" />
                                                            <div className="item-details">
                                                                <div className="item-name">{item.name}</div>
                                                                <div className="item-price-a">{item.price}</div>
                                                            </div>
                                                            <div className="item-actions">
                                                                <button
                                                                    className="add-cart-btn cursor-pointer"
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleAddToCart(item);
                                                                    }}
                                                                >
                                                                    상품 조회
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )
                                ))}
                            </>
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

export default WishlistB;

