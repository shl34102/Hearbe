import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Mail, Lock, Store, ShieldCheck, LogOut } from 'lucide-react';
import { memberAPI } from '../../services/memberAPI';
import { authAPI } from '../../services/authAPI';
import Swal from 'sweetalert2';
import '../MyPage/mypage-common.css';
import './MemberInfoC.css';
import logoC from '../../assets/logoC.png';

const MemberInfoC = () => {
    const navigate = useNavigate();

    const [userData, setUserData] = useState({
        userId: '',
        userName: '',
        email: '',
        phone: '',
    });
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const sidebarItems = [
        { id: 'member-info', label: '회원 정보', path: '/C/member-info' },
        { id: 'order-history', label: '주문 내역', path: '/C/order-history' },
        { id: 'wishlist', label: '찜한 상품', path: '/C/wishlist' },
        { id: 'cart', label: '장바구니', path: '/C/cart' },
    ];

    useEffect(() => {
        const fetchUserProfile = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await memberAPI.getProfile();

                const profileData = response.data || response;

                setUserData({
                    userId: localStorage.getItem('username') || '',
                    userName: profileData.username || profileData.name || '',
                    email: profileData.email || '',
                    phone: profileData.phoneNumber || profileData.phone || '',
                });
            } catch (err) {
                console.error('Failed to fetch user profile:', err);
                setError(err.message);

                if (err.message === '로그인이 필요합니다.' || err.message === '접근 권한이 없습니다.') {
                    localStorage.removeItem('accessToken');
                    localStorage.removeItem('refreshToken');
                    localStorage.removeItem('user');
                    localStorage.removeItem('username');
                    navigate('/C/login');
                    return;
                }

                const storedUsername = localStorage.getItem('username');
                const storedUser = localStorage.getItem('user');

                let fallbackData = {
                    userId: storedUsername || '',
                    userName: '',
                    email: '',
                    phone: ''
                };

                if (storedUser) {
                    try {
                        const parsed = JSON.parse(storedUser);
                        fallbackData.userId = fallbackData.userId || parsed.username || parsed.id || '';
                        fallbackData.userName = parsed.name || parsed.realName || '';
                        fallbackData.email = parsed.email || '';
                        fallbackData.phone = parsed.phone || '';
                    } catch (e) {
                        console.error('Failed to parse stored user data:', e);
                    }
                }

                setUserData(fallbackData);
            } finally {
                setIsLoading(false);
            }
        };

        fetchUserProfile();
    }, [navigate]);

    const handlePasswordReset = () => {
        navigate('/C/findPassword');
    };

    const handleWithdraw = () => {
        Swal.fire({
            title: '회원 탈퇴',
            text: '정말로 탈퇴하시겠습니까? 탈퇴 시 모든 정보가 삭제되며 복구할 수 없습니다.',
            icon: 'warning',
            input: 'password',
            inputLabel: '본인 확인을 위해 비밀번호를 입력해주세요.',
            inputPlaceholder: '비밀번호 입력',
            showCancelButton: true,
            confirmButtonColor: '#dc2626',
            cancelButtonColor: '#6b7280',
            confirmButtonText: '탈퇴하기',
            cancelButtonText: '취소',
            inputAttributes: {
                autocapitalize: 'off',
                autocorrect: 'off'
            }
        }).then(async (result) => {
            if (result.isConfirmed) {
                if (!result.value) {
                    Swal.fire('오류', '비밀번호를 입력해주세요.', 'error');
                    return;
                }

                try {
                    await authAPI.deleteAccount(result.value);

                    Swal.fire({
                        title: '탈퇴 완료',
                        text: '회원탈퇴가 완료되었습니다.',
                        icon: 'success',
                        confirmButtonColor: '#7c3aed'
                    }).then(() => {
                        localStorage.removeItem('accessToken');
                        localStorage.removeItem('refreshToken');
                        localStorage.removeItem('user');
                        localStorage.removeItem('username');
                        localStorage.removeItem('user_id');
                        localStorage.removeItem('user_name');
                        localStorage.removeItem('savedLoginId_c');
                        localStorage.removeItem('savedLoginPassword_C');
                        navigate('/main');
                    });
                } catch (error) {
                    console.error('Delete account failed:', error);
                    const msg = error.message || '';
                    if (msg.includes('비밀번호') || msg.includes('password') || msg.includes('mismatch')) {
                        Swal.fire('오류', '비밀번호가 일치하지 않습니다.', 'error');
                    } else {
                        Swal.fire('오류', '예상치 못한 오류가 발생했습니다.', 'error');
                    }
                }
            }
        });
    };

    const handleLogout = async () => {
        try {
            await authAPI.logout();
        } catch (error) {
            console.error('Logout failed:', error);
        } finally {
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('user');
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            navigate('/main');
        }
    };

    return (
        <div className="mypage-container">
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
                <aside className="mypage-sidebar">
                    <div className="sidebar-profile-card">
                        <div className="sidebar-avatar">
                            <User size={40} color="#7c3aed" />
                        </div>
                        <div className="sidebar-profile-info">
                            <h2 className="sidebar-name">{userData.userName || userData.userId}님</h2>
                            <span className="sidebar-badge">hearbe 회원</span>
                        </div>
                        <p className="sidebar-welcome">오늘도 즐거운 쇼핑 되세요!</p>
                    </div>

                    <div className="sidebar-menu-list">
                        {sidebarItems.map((item) => (
                            <button
                                key={item.id}
                                onClick={() => navigate(item.path)}
                                className={`mp-sidebar-item cursor-pointer ${item.id === 'member-info' ? 'active' : ''}`}
                                style={{ justifyContent: 'center', textAlign: 'center' }}
                            >
                                <span className="label">{item.label}</span>
                            </button>
                        ))}
                    </div>
                </aside>

                <main className="mypage-content">
                    <div className="content-stack">
                        {/* Profile Section */}
                        <section className="dashboard-card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div style={{
                                        width: '50px', height: '50px', borderRadius: '1rem',
                                        backgroundColor: '#f3e8ff', color: '#7c3aed',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                                    }}>
                                        <ShieldCheck size={28} />
                                    </div>
                                    <h2 className="card-title-lg" style={{ marginBottom: 0 }}>회원 정보</h2>
                                </div>
                            </div>
                            {isLoading ? (
                                <div style={{ textAlign: 'center', padding: '3rem', color: '#888' }}>
                                    회원정보를 불러오는 중...
                                </div>
                            ) : error ? (
                                <div style={{ textAlign: 'center', padding: '3rem', color: '#e53e3e' }}>
                                    {error}
                                </div>
                            ) : (
                                <div className="info-list-full">
                                    <div className="info-row-full" style={{ padding: '0.8rem 0' }}>
                                        <div className="row-icon-circle"><User size={20} /></div>
                                        <div className="row-content">
                                            <span className="row-label" style={{ fontSize: '1.3rem' }}>아이디</span>
                                            <span className="row-value" style={{ fontSize: '1.3rem' }}>{userData.userId || '-'}</span>
                                        </div>
                                    </div>
                                    <div className="info-row-full" style={{ padding: '0.8rem 0' }}>
                                        <div className="row-icon-circle"><Lock size={20} /></div>
                                        <div className="row-content">
                                            <span className="row-label" style={{ fontSize: '1.3rem' }}>비밀번호</span>
                                            <span className="row-value" style={{ fontSize: '1.3rem' }}>********</span>
                                        </div>
                                        <button className="small-action-btn cursor-pointer" onClick={handlePasswordReset}>재설정하기</button>
                                    </div>
                                    <div className="info-row-full" style={{ padding: '0.8rem 0' }}>
                                        <div className="row-icon-circle"><User size={20} /></div>
                                        <div className="row-content">
                                            <span className="row-label" style={{ fontSize: '1.3rem' }}>이름</span>
                                            <span className="row-value" style={{ fontSize: '1.3rem' }}>{userData.userName || '-'}</span>
                                        </div>
                                    </div>
                                    <div className="info-row-full" style={{ padding: '0.8rem 0' }}>
                                        <div className="row-icon-circle"><Mail size={20} /></div>
                                        <div className="row-content">
                                            <span className="row-label" style={{ fontSize: '1.3rem' }}>이메일</span>
                                            <span className="row-value" style={{ fontSize: '1.3rem' }}>{userData.email || '-'}</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </section>
                        <button className="withdraw-link cursor-pointer" onClick={handleWithdraw}>회원탈퇴</button>
                    </div>
                </main>
            </div>

            <footer className="landing-footer">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>

        </div>
    );
};

export default MemberInfoC;