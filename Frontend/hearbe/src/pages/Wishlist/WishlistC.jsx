import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Store, Heart, LogOut } from 'lucide-react';
import { wishlistAPI } from '../../services/wishlistAPI';
import { authAPI } from '../../services/authAPI';
import '../MyPage/mypage-common.css';
import './WishlistC.css';
import logoC from '../../assets/logoC.png';

const WishlistC = ({ onHome }) => {
    const navigate = useNavigate();

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

    // Wishlist state
    const [wishlists, setWishlists] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    // platformName 매핑 (영문 -> 한글)
    const platformDisplayNames = {
        'coupang': '쿠팡',
        'naver': '네이버',
        '11st': '11번가',
        'ssg': 'SSG',
        'gmarket': 'G마켓',
        'kurly': '컬리'
    };

    useEffect(() => {
        fetchWishlist();
    }, []);

    const fetchWishlist = async () => {
        try {
            setIsLoading(true);
            setError(null);
            const response = await wishlistAPI.getWishlist();

            if (response.items && response.items.length > 0) {
                const wishlistByMall = {};
                response.items.forEach(item => {
                    const rawName = item.platform_name || '';
                    const mallName = platformDisplayNames[rawName.toLowerCase()] || rawName;

                    if (!wishlistByMall[mallName]) {
                        wishlistByMall[mallName] = {
                            mall: mallName,
                            count: 0,
                            items: [],
                            wishlistUrl: item.wishlist_url // API에서 위시리스트 URL 연동
                        };
                    }
                    wishlistByMall[mallName].items.push({
                        id: item.wishlist_item_id,
                        name: item.product_name,
                        price: item.price || 0,
                        imgUrl: item.img_url,
                        productUrl: item.product_url,
                        tag: '',
                        icon: '❤️'
                    });
                    wishlistByMall[mallName].count++;
                });
                setWishlists(Object.values(wishlistByMall));
            } else {
                setWishlists([]);
            }
        } catch (err) {
            console.error('Failed to fetch wishlist:', err);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

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
                    <button className="nav-item-c cursor-pointer" onClick={onHome || (() => navigate('/C/mall'))}>
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
                                className={`mp-sidebar-item cursor-pointer ${item.id === 'wishlist' ? 'active' : ''}`}
                            >
                                <span className="label">{item.label}</span>
                            </button>
                        ))}
                    </div>
                </aside>

                {/* Main Content */}
                <main className="mypage-content">
                    <section className="dashboard-card full-height">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
                            <div style={{
                                width: '50px', height: '50px', borderRadius: '1rem',
                                backgroundColor: '#f3e8ff', color: '#7c3aed',
                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <Heart size={28} />
                            </div>
                            <h2 className="card-title-lg" style={{ marginBottom: 0 }}>찜한 상품</h2>
                        </div>
                        <div className="wishlist-content">
                            {isLoading ? (
                                <div className="wishlist-status-message">
                                    찜한 상품을 불러오는 중...
                                </div>
                            ) : error ? (
                                <div className="wishlist-error-message">
                                    {error}
                                </div>
                            ) : wishlists.length === 0 ? (
                                <div className="wishlist-status-message" style={{ width: '100%', display: 'flex', justifyContent: 'center', padding: '3rem', color: '#888', fontSize: '2rem', fontWeight: 'bold' }}>
                                    찜한 상품이 없습니다.
                                </div>
                            ) : (
                                wishlists.map((group, idx) => (
                                    <div key={idx} className="mall-wish-group">
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                <div className="mall-order-indicator"></div>
                                                <h3 className="mall-header-name" style={{ marginBottom: 0 }}>{group.mall} <span className="count-badge" style={{ marginLeft: '1rem' }}>{group.count}개</span></h3>
                                            </div>
                                        </div>

                                        <div className="group-items">
                                            {group.items.map((item) => (
                                                <div key={item.id} className="item-row-card">
                                                    <div className="item-row-left">
                                                        <div className="item-thumb">
                                                            {item.imgUrl ? (
                                                                <img src={item.imgUrl} alt={item.name} className="wishlist-item-image" />
                                                            ) : (
                                                                item.icon
                                                            )}
                                                        </div>
                                                        <div className="item-info-text">
                                                            <div className="item-name-lg">{item.name}</div>
                                                            <div className="item-price-lg">{item.price.toLocaleString()}원</div>
                                                        </div>
                                                    </div>
                                                    <button
                                                        className="btn-outline-sm wishlist-detail-btn cursor-pointer"
                                                        onClick={() => item.productUrl && window.open(item.productUrl, '_blank')}
                                                    >
                                                        상세 조회
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))
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

export default WishlistC;
