import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Store, LogOut, User } from 'lucide-react';
import logoA from '../../assets/logoA.png';
import { memberAPI } from '../../services/memberAPI';
import { authAPI } from '../../services/authAPI';
import './MemberInfoB.css';

const MemberInfoB = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const [userData, setUserData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const menuItems = [
        { id: 'profile', label: '회원 정보', path: '/B/member-info' },
        { id: 'orders', label: '주문 내역', path: '/B/order-history' },
        { id: 'wishlist', label: '찜한 상품', path: '/B/wishlist' },
        { id: 'cart', label: '장바구니', path: '/B/cart' },
        { id: 'card', label: <>장애인 복지<br />카드 변경</>, path: '/B/card-management' }
    ];

    const currentPath = location.pathname;

    // Phone number formatting helper
    const formatPhoneNumber = (phone) => {
        if (!phone) return '';
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 11) {
            return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 7)}-${cleaned.slice(7)}`;
        }
        return phone;
    };

    // Fetch user profile on mount
    useEffect(() => {
        const fetchUserProfile = async () => {
            try {
                setLoading(true);
                setError(null);
                const response = await memberAPI.getProfile();

                // username: 실제 이름 (user.getName())
                // phoneNumber: 전화번호
                // userType: 사용자 유형 (BLIND, LOW_VISION, GENERAL)
                setUserData({
                    name: response.data?.username || '-',
                    phone: formatPhoneNumber(response.data?.phoneNumber) || '-',
                    password: '******',
                    userType: response.data?.userType || '-'
                });
            } catch (err) {
                console.error('Failed to fetch user profile:', err);
                setError(err.message);

                // Redirect to login on 401
                if (err.message === '로그인이 필요합니다.') {
                    navigate('/B/login');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchUserProfile();
    }, [navigate]);

    const handleLogout = async () => {
        try {
            await authAPI.logout();
        } catch (err) {
            console.warn('Logout failed:', err);
        } finally {
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('savedLoginId');
            localStorage.removeItem('savedLoginPassword');
            localStorage.removeItem('userData');
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            localStorage.removeItem('user_name');
            navigate('/main');
        }
    };

    const showAlert = (message, type = 'success', onConfirm = null) => {
        Swal.fire({
            icon: type,
            text: message,
            background: '#141C29',
            color: '#FFF064',
            confirmButtonColor: '#FFF064',
            confirmButtonText: '<span style="color:#141C29">확인</span>'
        }).then(() => {
            if (onConfirm) onConfirm();
        });
    };

    const [isWithdrawModalOpen, setIsWithdrawModalOpen] = useState(false);
    const [withdrawPassword, setWithdrawPassword] = useState('');

    const handleWithdrawClick = () => {
        setIsWithdrawModalOpen(true);
        setWithdrawPassword('');
    };

    const handleConfirmWithdraw = async () => {
        if (!withdrawPassword) {
            showAlert("비밀번호를 입력해주세요.", "error");
            return;
        }

        try {
            await authAPI.deleteAccount(withdrawPassword);

            // Close password modal first
            setIsWithdrawModalOpen(false);

            // Show success alert
            showAlert("회원탈퇴가 완료되었습니다.", "success", () => {
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
                localStorage.removeItem('savedLoginId');
                localStorage.removeItem('savedLoginPassword');
                localStorage.removeItem('userData');
                localStorage.removeItem('user_id');
                localStorage.removeItem('username');
                localStorage.removeItem('user_name');
                navigate('/');
            });

        } catch (err) {
            console.error('Withdrawal failed:', err);
            if (err.message && (err.message.includes('비밀번호') || err.message.includes('password') || err.message.includes('mismatch'))) {
                showAlert("비밀번호가 일치하지 않습니다.", "error");
            } else {
                showAlert("비밀번호가 일치하지 않습니다.", "error");
            }
        }
    };

    const handleRetry = () => {
        setError(null);
        setLoading(true);
        // Re-trigger useEffect by navigating to same route
        navigate(location.pathname, { replace: true });
    };

    return (
        <div className="memberinfo-container">
            <img
                src={logoA}
                alt="Logo"
                className="memberinfo-logo-left cursor-pointer"
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

            <div className="memberinfo-content">
                {/* Sidebar Navigation - Omit avatar, keep menu in a card */}
                <aside className="memberinfo-sidebar">
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

                {/* Main Content - Card structure */}
                <main className="memberinfo-main">
                    <div className="content-card">
                        <h2 className="content-title">
                            <User size={64} color="#FFF064" />
                            회원 정보
                        </h2>

                        {loading ? (
                            <div className="loading-state">
                                <div className="spinner"></div>
                                <p>사용자 정보를 불러오는 중...</p>
                            </div>
                        ) : error ? (
                            <div className="error-state">
                                <p className="error-message">사용자 정보를 불러오지 못했습니다.</p>
                                <p className="error-detail">{error}</p>
                                <button className="retry-btn cursor-pointer" onClick={handleRetry}>
                                    다시 시도
                                </button>
                            </div>
                        ) : userData ? (
                            <>
                                <div className="member-info-list">
                                    <div className="member-info-row">
                                        <div className="member-col-left">
                                            <span className="member-label">아이디</span>
                                        </div>
                                        <div className="member-col-right">
                                            <span className="member-value">{localStorage.getItem('username') || '-'}</span>
                                        </div>
                                    </div>
                                    <div className="member-info-row">
                                        <div className="member-col-left">
                                            <span className="member-label">비밀번호</span>
                                        </div>
                                        <div className="member-col-right">
                                            <div className="password-wrapper">
                                                <span className="member-value">{userData.password}</span>
                                                <button
                                                    className="password-change-btn cursor-pointer"
                                                    onClick={() => navigate('/B/changePassword')}
                                                >
                                                    변경하기
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="member-info-row">
                                        <div className="member-col-left">
                                            <span className="member-label">이름</span>
                                        </div>
                                        <div className="member-col-right">
                                            <span className="member-value">{userData.name}</span>
                                        </div>
                                    </div>
                                    <div className="member-info-row">
                                        <div className="member-col-left">
                                            <span className="member-label">휴대폰번호</span>
                                        </div>
                                        <div className="member-col-right">
                                            <span className="member-value">{userData.phone}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="logout-section">
                                    <span className="logout-link cursor-pointer" onClick={handleWithdrawClick}>
                                        회원탈퇴
                                    </span>
                                </div>
                            </>
                        ) : null}
                    </div>
                </main>
            </div>

            {/* Withdraw Password Modal */}
            {isWithdrawModalOpen && (
                <div className="modal-overlay">
                    <div className="modal-box">
                        <h1 className="modal-title">회원 탈퇴</h1>
                        <p className="modal-desc">
                            정말로 탈퇴하시겠습니까?<br />
                            탈퇴 시 모든 정보가 삭제됩니다.<br />
                            본인 확인을 위해 비밀번호를 입력해주세요.
                        </p>
                        <input
                            type="password"
                            className="modal-input"
                            value={withdrawPassword}
                            onChange={(e) => setWithdrawPassword(e.target.value)}
                            placeholder="비밀번호 입력"
                            maxLength={6}
                        />
                        <div className="modal-actions">
                            <button
                                className="modal-btn cancel cursor-pointer"
                                onClick={() => setIsWithdrawModalOpen(false)}
                            >
                                취소
                            </button>
                            <button
                                className="modal-btn confirm cursor-pointer"
                                onClick={handleConfirmWithdraw}
                            >
                                탈퇴하기
                            </button>
                        </div>
                    </div>
                </div>
            )}


            <footer className="landing-footer-a">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default MemberInfoB;
