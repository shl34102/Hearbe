import React from 'react';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';
import { ShoppingCart, User, ArrowUpRight, LogOut } from 'lucide-react';
import './SelectMallC.css';
import coupangLogo from '../../assets/coupang_logo.png';
import naverPlusLogo from '../../assets/C/naver_plus_logo.png';
import gmarketLogo from '../../assets/C/Gmarket_logo.png';
import kurlyLogo from '../../assets/C/Kurly_logo.png';
import st11Logo from '../../assets/C/11st_logo.png';
import ssgLogo from '../../assets/C/ssg_logo.png';
import logoC from '../../assets/logoC.png';
import { authAPI } from '../../services/authAPI';

const SelectMallC = () => {
    const navigate = useNavigate();

    const handleLogout = () => {
        Swal.fire({
            title: '로그아웃 하시겠습니까?',
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#7c3aed',
            cancelButtonColor: '#d33',
            confirmButtonText: '로그아웃',
            cancelButtonText: '취소'
        }).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    await authAPI.logout();
                } catch (error) {
                    console.error('Logout failed:', error);
                } finally {
                    localStorage.removeItem('accessToken');
                    localStorage.removeItem('refreshToken');
                    localStorage.removeItem('user_id');
                    localStorage.removeItem('username');
                    localStorage.removeItem('user_name');
                    navigate('/main');
                }
            }
        });
    };

    const malls = [
        { id: 'coupang', name: '쿠팡', desc: '', color: '#E2211C', initial: 'C', logo: coupangLogo, logoSize: 300, url: 'https://www.coupang.com', disabled: false },
        { id: 'naver', name: '네이버 쇼핑', desc: '서비스 준비 중입니다.', color: '#03C75A', initial: 'N', logo: naverPlusLogo, logoSize: 240, url: '', disabled: true },
        { id: '11st', name: '11번가', desc: '서비스 준비 중입니다.', color: '#FF4B4B', initial: '1', logo: st11Logo, logoSize: 200, url: '', disabled: true },
    ];

    const [isScrolled, setIsScrolled] = React.useState(false);

    React.useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 50);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const handleSelect = (mall) => {
        if (mall.disabled) return;
        window.open(mall.url, '_blank');
    };

    return (
        <div className="select-mall-page-c">
            <header className={`mall-header-c ${isScrolled ? 'scrolled' : ''}`}>
                <div className="header-left-c">
                    <img
                        src={logoC}
                        alt="HearBe Logo"
                        className="header-logo-c"
                        onClick={() => navigate('/main')}
                        style={{ height: '60px', cursor: 'pointer', objectFit: 'contain' }}
                    />
                </div>

                <div className="header-right-c">

                    <button className="nav-item-c cursor-pointer" onClick={() => navigate('/C/cart')}>
                        <div className="nav-icon-c"><ShoppingCart size={24} /></div>
                        <span>장바구니</span>
                    </button>
                    <button className="nav-item-c cursor-pointer" onClick={() => navigate('/C/member-info')}>
                        <div className="nav-icon-c"><User size={24} /></div>
                        <span>마이페이지</span>
                    </button>
                    <button className="nav-item-c cursor-pointer" onClick={handleLogout}>
                        <div className="nav-icon-c"><LogOut size={24} /></div>
                        <span>로그아웃</span>
                    </button>
                </div>
            </header >

            < main className="mall-main-c" >
                <div className="mall-hero-c">
                    <h1 className="mall-main-title-c">어디서 쇼핑을 시작할까요?</h1>
                    <div className="voice-guide-badge-c">
                        <span className="badge-text-c">[SPACEBAR]</span>를 눌러 음성 명령이 가능합니다
                    </div>
                </div>

                <div className="mall-grid-container-c">
                    {malls.map((mall, index) => (
                        <div
                            key={mall.id}
                            className={`mall-card-new-c ${mall.disabled ? 'mall-card-disabled' : 'cursor-pointer'}`}
                            onClick={() => handleSelect(mall)}
                        >
                            <div className="card-top-row-c">
                                <div className="card-title-row-c">
                                    <div className="card-num-badge-c" style={{ backgroundColor: mall.disabled ? '#cbd5e1' : mall.color }}>
                                        {index + 1}
                                    </div>
                                    <h3 className="mall-card-name-c">{mall.name}</h3>
                                </div>
                                {!mall.disabled && <ArrowUpRight className="card-link-icon-c" size={20} />}
                            </div>

                            <img src={mall.logo} alt={mall.name} className="card-watermark-logo-c" style={mall.logoSize ? { width: `${mall.logoSize}px` } : {}} />

                            <div className="card-content-c">
                                {!mall.disabled && <p className="mall-card-desc-c">{mall.desc}</p>}
                            </div>

                            <div className="card-footer-c">
                                <span className="open-store-text-c">{mall.disabled ? 'COMING SOON' : 'OPEN STORE'}</span>
                                {!mall.disabled && <span className="open-store-arrow-c">→</span>}
                            </div>
                        </div>
                    ))}
                </div>
            </main >

            <footer className="landing-footer">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>

            <div className="floating-question-c cursor-pointer">?</div>
        </div >
    );
};

export default SelectMallC;
