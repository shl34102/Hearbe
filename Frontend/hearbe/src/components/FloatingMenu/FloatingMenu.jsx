import { useState } from 'react';
import PropTypes from 'prop-types';
import './FloatingMenu.css';

/**
 * 플로팅 메뉴 버튼 (A형 쇼핑몰 브라우저에서 사용)
 */
const FloatingMenu = ({ onShare, onMyPage, onCart }) => {
    const [isOpen, setIsOpen] = useState(false);

    const toggleMenu = () => {
        setIsOpen(!isOpen);
    };

    const handleShare = () => {
        setIsOpen(false);
        onShare();
    };

    const handleMyPage = () => {
        setIsOpen(false);
        onMyPage();
    };

    const handleCart = () => {
        setIsOpen(false);
        onCart();
    };

    return (
        <div className="floating-menu-container">
            {isOpen && (
                <div className="floating-menu-items">
                    <button className="menu-item" onClick={handleMyPage}>
                        마이페이지
                    </button>
                    <button className="menu-item" onClick={handleCart}>
                        장바구니
                    </button>
                    <button className="menu-item menu-item-share" onClick={handleShare}>
                        공유
                    </button>
                </div>
            )}

            <button
                className={`floating-menu-button ${isOpen ? 'open' : ''}`}
                onClick={toggleMenu}
                aria-label="메뉴"
            >
                <span className="hamburger-line"></span>
                <span className="hamburger-line"></span>
                <span className="hamburger-line"></span>
            </button>
        </div>
    );
};

FloatingMenu.propTypes = {
    onShare: PropTypes.func.isRequired,
    onMyPage: PropTypes.func,
    onCart: PropTypes.func
};

export default FloatingMenu;
