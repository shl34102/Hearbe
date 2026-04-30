import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useCallback } from 'react';
import Swal from 'sweetalert2';
import './StoreBrowserB.css';
import iconCart from '../../assets/icon-cart.png';
import iconShare from '../../assets/icon-share.png';
import iconCard from '../../assets/icon-cart.png';
import logo from '../../assets/logoA.png';
import { cartAPI } from '../../services/cartAPI';
import { shareCodeService } from '../../services/shareCodeService';
import FloatingMenu from '../../components/FloatingMenu/FloatingMenu';
import ShareCodeModal from '../../components/ShareCode/ShareCodeModal';
import { usePeerShare } from '../../hooks/peerjs/usePeerShare';


const StoreBrowser = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { mallId } = useParams();

    // Map mallId to URL
    const getMallUrl = (id) => {
        const urlMap = {
            '1': 'https://www.coupang.com',
            '2': 'https://m.shopping.naver.com/',
            '3': 'https://m.11st.co.kr/',
            '4': 'https://m.ssg.com/'
        };
        return urlMap[id] || 'https://m.shopping.naver.com/';
    };

    const searchParams = new URLSearchParams(location.search);
    const queryUrl = searchParams.get('url');
    const autoShare = searchParams.get('autoshare') === '1';
    const url = queryUrl ? decodeURIComponent(queryUrl) : (location.state?.url || getMallUrl(mallId));
    const isExtensionFlow = Boolean(queryUrl || autoShare);

    // PeerJS Hooks
    const { shareCode, isSharing, startSharing, stopSharing, error: peerError } = usePeerShare();

    // UI States
    const [showShareModal, setShowShareModal] = useState(false);
    const [isLoadingCode, setIsLoadingCode] = useState(false);
    const [tempCode, setTempCode] = useState(null);
    const [showAddCartModal, setShowAddCartModal] = useState(false);

    // Product Info State
    const [productInfo, setProductInfo] = useState({
        name: '',
        price: '',
        url: '',
        img_url: ''
    });

    // Error handling
    useEffect(() => {
        if (peerError) {
            Swal.fire({
                icon: 'error',
                text: `화면 공유 에러: ${peerError}`,
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    }, [peerError]);

    // Platform Checks
    const isNaver = url.includes('naver');

    // Platform cart URLs
    const getPlatformCartUrl = () => {
        if (url.includes('coupang')) {
            return 'https://www.coupang.com';
        } else if (url.includes('naver')) {
            return 'https://shopping.naver.com/cart';
        } else if (url.includes('11st')) {
            return 'https://m.11st.co.kr/MW/MyOrder/MyCart';
        } else if (url.includes('ssg')) {
            return 'https://m.ssg.com/cart/dmsShppCartList.ssg';
        }
        return null;
    };

    const handleSimulateAddCart = async () => {
        const dummyItems = [
            { name: '네이버 인기 생수 2L x 6', price: 5900, img_url: 'https://via.placeholder.com/150?text=Water' },
            { name: '프리미엄 원두 커피 500g', price: 18500, img_url: 'https://via.placeholder.com/150?text=Coffee' },
            { name: '친환경 세탁 세제 3L', price: 12900, img_url: 'https://via.placeholder.com/150?text=Detergent' }
        ];
        const randomItem = dummyItems[Math.floor(Math.random() * dummyItems.length)];

        try {
            const itemData = {
                platformId: 2, // Naver
                name: randomItem.name,
                url: url,
                img_url: randomItem.img_url,
                price: randomItem.price
            };

            await cartAPI.addToCart(itemData);
            Swal.fire({
                icon: 'success',
                text: `[시뮬레이션] 장바구니에 '${randomItem.name}'이(가) 추가되었습니다!`,
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: `시뮬레이션 추가 실패: ${error.message}`,
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    // --- Handlers ---

    const handleShareClick = useCallback(async () => {
        setIsLoadingCode(true);
        setShowShareModal(true);

        try {
            // Call backend API to generate code
            const code = await shareCodeService.createCode();
            setTempCode(code);
        } catch (error) {
            console.error('Create code error:', error);
            Swal.fire({
                icon: 'error',
                text: '공유 코드를 생성할 수 없습니다. (백엔드 연결 확인)',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            setShowShareModal(false);
        } finally {
            setIsLoadingCode(false);
        }
    }, []);

    useEffect(() => {
        if (autoShare) {
            handleShareClick();
        }
    }, [autoShare, handleShareClick]);

    const handleEnterShare = async () => {
        try {
            await startSharing(tempCode);
            setShowShareModal(false);
        } catch (err) {
            console.error('Failed to start sharing:', err);
        }
    };

    const handleEndShare = () => {
        stopSharing();
    };

    const handleCart = () => navigate('/B/cart');

    const handleMyPage = () => navigate('/B/mypage');

    const handlePlatformCart = () => {
        const cartUrl = getPlatformCartUrl();
        if (cartUrl) {
            window.open(cartUrl, '_blank');
        } else {
            Swal.fire({
                icon: 'info',
                text: '현재 쇼핑몰의 장바구니 URL을 찾을 수 없습니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    // const handleAddToMyCart = () => {
    //     setIsMenuOpen(false);
    //     setShowAddCartModal(true);
    // };

    const handleProductInfoChange = (field, value) => {
        setProductInfo(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmitProduct = async () => {
        if (!productInfo.name || !productInfo.price) {
            Swal.fire({
                icon: 'warning',
                text: '상품명과 가격은 필수 항목입니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }

        try {
            // Determine platform ID based on current URL
            let platformId = 1; // Default to Coupang
            if (url.includes('naver')) platformId = 2;
            else if (url.includes('11st')) platformId = 3;
            else if (url.includes('ssg')) platformId = 4;

            const itemData = {
                platformId,
                name: productInfo.name,
                url: productInfo.url || url,
                img_url: productInfo.img_url || 'https://via.placeholder.com/80',
                price: parseInt(productInfo.price)
            };

            await cartAPI.addToCart(itemData);
            Swal.fire({
                icon: 'success',
                text: '장바구니에 상품이 추가되었습니다!',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            setShowAddCartModal(false);
            setProductInfo({ name: '', price: '', url: '', img_url: '' });
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: `장바구니 추가 실패: ${error.message}`,
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    const hideOpenInNewTabNotice = true;

    return (
        <div className={`store-container${hideOpenInNewTabNotice ? ' hide-new-tab-notice' : ''}`}>

            {/* 쇼핑몰은 새 탭에서 열리고, 이 화면은 공유 제어용으로만 사용 */}

            {/* --- Sharing Mode UI --- */}
            {isSharing && (
                <>
                    {/* Top Sharing Banner */}
                    <div className="sharing-header">
                        <div className="sharing-pill">화면 공유 중 (코드: {shareCode})</div>
                        <div className="participant-pill">
                            <img src={logo} alt="User" className="p-icon" />
                            <span>참가자 (1명)</span>
                        </div>
                    </div>

                    {/* Bottom Control Bar */}
                    <div className="sharing-bottom-bar">
                        <button className="sharing-btn cursor-pointer" onClick={handlePlatformCart}>
                            <img src={iconCart} alt="Cart" className="s-icon" />
                            <span>쇼핑몰 장바구니</span>
                        </button>
                        <button className="sharing-btn cursor-pointer" onClick={handleCart}>
                            <img src={iconCart} alt="My Cart" className="s-icon" />
                            <span>내 장바구니</span>
                        </button>
                        <button className="sharing-btn primary cursor-pointer">
                            <img src={iconCard} alt="Buy" className="s-icon" />
                            <span>바로구매</span>
                        </button>
                        {isNaver && (
                            <button className="sharing-btn cursor-pointer" onClick={handleSimulateAddCart} style={{ backgroundColor: '#03C75A', color: 'white' }}>
                                <img src={iconCart} alt="Simulate" className="s-icon" />
                                <span>네이버 담기 (시뮬)</span>
                            </button>
                        )}
                        <button className="sharing-btn highlight cursor-pointer" onClick={handleEndShare}>
                            <img src={iconShare} alt="Share" className="s-icon" />
                            <span>공유 종료</span>
                        </button>
                    </div>
                </>
            )}


            {/* --- Normal Mode UI (Hidden when sharing) --- */}
            {!isSharing && (
                <FloatingMenu
                    onShare={handleShareClick}
                    onMyPage={handleMyPage}
                    onCart={handleCart}
                />
            )}

            {/* Share Modal */}
            <ShareCodeModal
                isOpen={showShareModal}
                onClose={() => setShowShareModal(false)}
                onStart={handleEnterShare}
                shareCode={tempCode}
                isLoading={isLoadingCode}
            />

            {/* Add to Cart Modal */}
            {showAddCartModal && (
                <div className="share-modal-overlay">
                    <div className="share-modal-content add-cart-modal">
                        <div className="share-modal-title">내 장바구니에 담기</div>
                        <div className="product-input-group">
                            <input type="text" placeholder="상품명 *" value={productInfo.name} onChange={(e) => handleProductInfoChange('name', e.target.value)} className="product-input" />
                            <input type="number" placeholder="가격 *" value={productInfo.price} onChange={(e) => handleProductInfoChange('price', e.target.value)} className="product-input" />
                            <input type="text" placeholder="상품 URL (선택)" value={productInfo.url} onChange={(e) => handleProductInfoChange('url', e.target.value)} className="product-input" />
                            <input type="text" placeholder="이미지 URL (선택)" value={productInfo.img_url} onChange={(e) => handleProductInfoChange('img_url', e.target.value)} className="product-input" />
                        </div>
                        <div className="share-modal-btns">
                            <button className="sm-btn cancel cursor-pointer" onClick={() => { setShowAddCartModal(false); setProductInfo({ name: '', price: '', url: '', img_url: '' }); }}>취소</button>
                            <button className="sm-btn confirm cursor-pointer" onClick={handleSubmitProduct}>추가</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default StoreBrowser;
