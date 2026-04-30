import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Store, LogOut, CreditCard } from 'lucide-react';
import logoA from '../../assets/logoA.png';
import iconCamera from '../../assets/icon-camera.png';
import iconCard from '../../assets/icon-card.png';
import { authAPI } from '../../services/authAPI';
import './CardManagementB.css';

const CardManagementB = () => {
    const navigate = useNavigate();
    const location = useLocation();

    // Initial card data (loaded from API)
    const [cardData, setCardData] = useState({
        company: '',
        number: '',
        expiry: '',
        cvc: ''
    });

    // Modal states
    const [showModal, setShowModal] = useState(false);
    const [modalStep, setModalStep] = useState('camera'); // 'camera' or 'form'
    const [formData, setFormData] = useState({
        company: '',
        number: '',
        expiry: '',
        cvc: ''
    });

    // Camera logic
    const videoRef = useRef(null);
    const [stream, setStream] = useState(null);

    const startCamera = async () => {
        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
            setStream(mediaStream);
            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
            }
        } catch (err) {
            console.error("Error accessing camera:", err);
        }
    };

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
    };

    const loadWelfareCard = async () => {
        try {
            const response = await authAPI.getWelfareCard();
            const data = response?.data || response;
            const cardCompany = data?.cardCompany || data?.card_company || '';
            const cardNumber = data?.cardNumber || data?.card_number || '';
            const expirationDate = data?.expirationDate || data?.expiration_date || '';
            const cvcValue = data?.cvc || localStorage.getItem('welfare_cvc') || '';
            setCardData({
                company: cardCompany,
                number: cardNumber,
                expiry: formatExpiryFromDate(expirationDate),
                cvc: cvcValue
            });
        } catch (error) {
            console.warn('Failed to load welfare card:', error);
        }
    };

    useEffect(() => {
        loadWelfareCard();
    }, []);

    // Camera modal management
    useEffect(() => {
        if (showModal && modalStep === 'camera') {
            startCamera();
        } else {
            stopCamera();
        }
        return () => {
            stopCamera();
        };
    }, [showModal, modalStep]);

    // Stream connection
    useEffect(() => {
        if (stream && videoRef.current) {
            videoRef.current.muted = true;
            videoRef.current.srcObject = stream;
            videoRef.current.play()
                .catch(e => console.error("video play fail:", e));
        }
    }, [stream, modalStep]);

    const handleChangeClick = () => {
        setShowModal(true);
        setModalStep('camera');
    };

    const handleSnap = () => {
        setFormData({
            company: cardData.company,
            number: cardData.number,
            expiry: cardData.expiry,
            cvc: cardData.cvc
        });
        setModalStep('form');
    };

    const formatExpiry = (value) => {
        const digits = value.replace(/[^0-9]/g, '').slice(0, 4);
        if (digits.length <= 2) return digits;
        return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    };

    const formatExpiryFromDate = (dateString) => {
        if (!dateString) return '';
        if (dateString.includes('/')) {
            return dateString;
        }
        const parts = dateString.split('-');
        if (parts.length < 2) return '';
        const mm = parts[1];
        const yy = parts[0].slice(-2);
        return `${mm}/${yy}`;
    };

    const formatCardNumber = (value) => {
        const digits = value.replace(/[^0-9]/g, '').slice(0, 16);
        return digits;
    };

    const handleFormChange = (e) => {
        const { name, value } = e.target;
        if (name === 'number') {
            setFormData((prev) => ({ ...prev, number: formatCardNumber(value) }));
            return;
        }
        if (name === 'expiry') {
            setFormData((prev) => ({ ...prev, expiry: formatExpiry(value) }));
            return;
        }
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const maskCardNumber = (value) => {
        if (!value) return '';
        const digits = value.replace(/[^0-9]/g, '');
        if (digits.length <= 4) return digits;
        const maskedLength = Math.max(0, digits.length - 4);
        return `${'*'.repeat(maskedLength)}${digits.slice(-4)}`;
    };

    const handleCardRegister = async () => {
        const cardNumberNormalized = formData.number.replace(/\s+/g, '');

        if (!formData.company || !cardNumberNormalized || !formData.expiry || !formData.cvc) {
            Swal.fire({
                icon: 'warning',
                text: '복지카드 정보를 모두 입력해주세요.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }
        const expPattern = /^(0[1-9]|1[0-2])\/\d{2}$/;
        if (!expPattern.test(formData.expiry)) {
            Swal.fire({
                icon: 'warning',
                text: '유효기간은 MM/YY 형식으로 입력해주세요.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }
        const cardPattern = /^\d{16}$/;
        if (!cardPattern.test(cardNumberNormalized)) {
            Swal.fire({
                icon: 'warning',
                text: '카드번호는 숫자 16자리로 입력해주세요.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }
        const cvcPattern = /^\d{3}$/;
        if (!cvcPattern.test(formData.cvc)) {
            Swal.fire({
                icon: 'warning',
                text: 'CVC는 3자리 숫자여야 합니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }

        try {
            await authAPI.updateWelfareCard({
                card_company: formData.company,
                card_number: cardNumberNormalized,
                expiration_date: formData.expiry,
                cvc: formData.cvc
            });
            localStorage.setItem('welfare_cvc', formData.cvc);
            await loadWelfareCard();
            setShowModal(false);
            setModalStep('camera');
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || '복지카드 정보 저장에 실패했습니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    const handleModalClose = () => {
        setShowModal(false);
        setModalStep('camera');
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

    return (
        <div className="cardmgmt-container">
            <img
                src={logoA}
                alt="Logo"
                className="cardmgmt-logo-left cursor-pointer"
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

            <div className="cardmgmt-content">
                {/* Sidebar */}
                <aside className="cardmgmt-sidebar">
                    <div className="sidebar-menu-card">
                        <nav className="sidebar-nav">
                            {menuItems.map(item => (
                                <button
                                    key={item.id}
                                    className={`sidebar-item ${currentPath === item.path ? 'active' : ''} cursor-pointer`}
                                    onClick={() => navigate(item.path)}
                                >
                                    {item.label}
                                </button>
                            ))}
                        </nav>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="cardmgmt-main">
                    <div className="content-card">
                        <h2 className="content-title">
                            <CreditCard size={64} color="#FFF064" />
                            장애인 복지카드 변경하기
                        </h2>

                        {/* Current Card Display */}
                        <div className="current-card-display">
                            <div className="card-info-row">
                                <span className="card-label">카드사</span>
                                <span className="card-value">{cardData.company}</span>
                            </div>
                            <div className="card-info-row">
                                <span className="card-label">복지카드 번호</span>
                                <span className="card-value">{maskCardNumber(cardData.number)}</span>
                            </div>
                            <div className="card-info-row-flex">
                                <div className="card-info-col">
                                    <span className="card-label">유효기간</span>
                                    <span className="card-value">{cardData.expiry}</span>
                                </div>
                                <div className="card-info-col">
                                    <span className="card-label">CVC</span>
                                    <span className="card-value">***</span>
                                </div>
                            </div>
                        </div>

                        <button className="change-card-btn cursor-pointer" onClick={handleChangeClick}>
                            변경하기
                        </button>
                    </div>
                </main>
            </div>

            {/* Camera Modal */}
            {showModal && (
                <div className="card-modal-overlay">
                    <div className="card-modal-box" onClick={(e) => e.stopPropagation()}>
                        {/* Close Button */}
                        <div className="card-modal-close cursor-pointer" onClick={handleModalClose}>X</div>

                        {modalStep === 'camera' ? (
                            // Camera Step
                            <>
                                <div className="card-modal-title">카드 촬영</div>
                                <div className="card-modal-desc">장애인 복지카드를 촬영해주세요.</div>

                                <div className="card-camera-area">
                                    {stream ? (
                                        <video ref={videoRef} autoPlay playsInline muted className="card-video-stream"></video>
                                    ) : (
                                        <>
                                            <div className="card-camera-text">카메라 연결 중...</div>
                                            <img src={iconCamera} alt="Camera" className="card-camera-icon" />
                                        </>
                                    )}
                                </div>

                                {stream && (
                                    <div className="card-shutter-button cursor-pointer" onClick={handleSnap}>
                                        <div className="card-shutter-inner"></div>
                                    </div>
                                )}
                            </>
                        ) : (
                            // Form Step
                            <>
                                <div className="card-form-content">
                                    <div className="card-form-header-area">
                                        <img src={iconCard} alt="card" className="small-card-icon" />
                                        <span>장애인 복지카드 정보</span>
                                    </div>

                                    <div className="card-modal-desc">인식된 정보를 확인해주세요.</div>

                                    <div className="form-field-group">
                                        <label>카드사</label>
                                        <input
                                            type="text"
                                            name="company"
                                            value={formData.company}
                                            onChange={handleFormChange}
                                            className="card-modal-input"
                                        />
                                    </div>

                                    <div className="form-field-group">
                                        <label>복지카드 번호</label>
                                        <input
                                            type="text"
                                            name="number"
                                            value={formData.number}
                                            onChange={handleFormChange}
                                            className="card-modal-input"
                                        />
                                    </div>

                                    <div className="form-row-group">
                                        <div className="form-field-group half">
                                            <label>유효기간</label>
                                            <input
                                                type="text"
                                                name="expiry"
                                                value={formData.expiry}
                                                onChange={handleFormChange}
                                                placeholder="MM/YY"
                                                maxLength={5}
                                                className="card-modal-input"
                                            />
                                        </div>
                                        <div className="form-field-group half">
                                            <label>CVC</label>
                                            <input
                                                type="text"
                                                name="cvc"
                                                value={formData.cvc}
                                                onChange={handleFormChange}
                                                className="card-modal-input"
                                            />
                                        </div>
                                    </div>

                                    <div className="card-button-group">
                                        <button className="card-retake-btn cursor-pointer" onClick={() => setModalStep('camera')}>다시 촬영</button>
                                        <button className="card-register-btn cursor-pointer" onClick={handleCardRegister}>카드 변경</button>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}

            <footer className="landing-footer-a">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default CardManagementB;
