import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingCart, User, LogOut } from 'lucide-react';
import iconCoupang from '../../assets/coupang_logo.png';
import iconNaver from '../../assets/C/naver_plus_logo.png';
import icon11st from '../../assets/C/11st_logo.png';
import iconSsg from '../../assets/C/ssg_logo.png';
import logoA from '../../assets/logoA.png';
import { authAPI } from '../../services/authAPI';
import Swal from 'sweetalert2';
import './SelectMallB.css';

const SelectMallB = () => {
    const navigate = useNavigate();

    const malls = [
        { id: '1', name: '쿠팡', logo: iconCoupang, url: 'https://www.coupang.com', color: '#E2211C', disabled: false },
        { id: '2', name: '네이버 쇼핑', logo: iconNaver, url: '', color: '#03C75A', disabled: true },
        { id: '3', name: '11번가', logo: icon11st, url: '', color: '#FF4B4B', disabled: true },
    ];

    const handleSelectMall = (mall) => {
        if (mall.disabled) return;
        window.open(mall.url, '_blank', 'noopener,noreferrer');
    };

    const handleLogout = () => {
        Swal.fire({
            title: '로그아웃 하시겠습니까?',
            icon: 'question',
            showCancelButton: true,
            background: '#141C29',
            color: '#FFF064',
            confirmButtonColor: '#FFF064',
            cancelButtonColor: 'transparent',
            confirmButtonText: '<span style="color:#141C29">로그아웃</span>',
            cancelButtonText: '<span style="color:#FFF064">취소</span>'
        }).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    await authAPI.logout();
                } catch (err) {
                    console.warn('Logout failed:', err);
                } finally {
                    localStorage.clear();
                    navigate('/main');
                }
            }
        });
    };

    return (
        <div className="select-mall-a-container">
            {/* Logo */}
            <img
                src={logoA}
                alt="Logo"
                className="select-mall-a-logo cursor-pointer"
                onClick={() => navigate('/main')}
            />

            {/* Top Navigation */}
            <header className="select-mall-a-header">
                <div className="header-actions-a">
                    <button className="header-btn-a cursor-pointer" onClick={() => navigate('/B/cart')}>
                        <ShoppingCart size={56} />
                        <span>카트</span>
                    </button>
                    <button className="header-btn-a cursor-pointer" onClick={() => navigate('/B/member-info')}>
                        <User size={56} />
                        <span>마이</span>
                    </button>
                    <button className="header-btn-a cursor-pointer" onClick={handleLogout}>
                        <LogOut size={56} />
                        <span>로그아웃</span>
                    </button>
                </div>
            </header>

            {/* Main Content */}
            <main className="select-mall-a-main">
                <div className="mall-list-a">
                    {malls.map((mall, index) => (
                        <button
                            key={mall.id}
                            className={`mall-item-a ${mall.disabled ? 'disabled' : 'cursor-pointer'}`}
                            onClick={() => handleSelectMall(mall)}
                        >
                            <div className="mall-num-a" style={{ backgroundColor: mall.disabled ? '#555' : mall.color }}>{index + 1}</div>
                            <div className="mall-info-a">
                                <span className="mall-name-a">{mall.name}</span>
                                <img src={mall.logo} alt={mall.name} className="mall-logo-img-a" />
                            </div>
                            {!mall.disabled && <div className="mall-arrow-a">→</div>}
                        </button>
                    ))}
                </div>
            </main>

            <footer className="select-mall-a-footer">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default SelectMallB;
