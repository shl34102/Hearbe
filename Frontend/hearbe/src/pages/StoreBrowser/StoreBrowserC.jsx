import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Share2, ShoppingCart, User, Menu, X, Home, ArrowUpRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import MyPageC from '../MyPage/MyPageC';
import CartC from '../Cart/CartC';
import './StoreBrowserC.css';

const StoreBrowserC = ({ mallName: propName, mallUrl: propUrl, onBack, onHome, onMyPage }) => {
    const location = useLocation();
    const navigate = useNavigate();
    const { name: stateName, url: stateUrl } = location.state || {};

    const mallName = propName || stateName || '쇼핑몰';
    const mallUrl = propUrl || stateUrl || 'https://m.shopping.naver.com/';

    const [showMainMenu, setShowMainMenu] = useState(false);
    const [showMeetingCode, setShowMeetingCode] = useState(false);
    const [meetingCode, setMeetingCode] = useState('');
    const [showMeetingRoom, setShowMeetingRoom] = useState(false);
    // showCart state - used for cart overlay
    const [showCart, setShowCart] = useState(false);
    const [showMyPage, setShowMyPage] = useState(false);
    const [participants, setParticipants] = useState([
        { id: 1, name: '나 (방장)', role: 'host', isMe: true }
    ]);

    /**
     * [DB Integration Point]
     * 향후 백엔드(WebSocket/Socket.io 등) 연결 시 
     * 참가자 참여/이탈 이벤트를 받아 setParticipants를 업데이트하는 로직이 올 위치입니다.
     */
    // const fetchParticipants = async () => { ... }

    const handleShareButtonClick = () => {
        handleShareStart();
        setShowMainMenu(false); // Close main menu when share button is clicked
    };

    const handleShareStart = () => {
        const newCode = Math.floor(1000 + Math.random() * 9000).toString();
        setMeetingCode(newCode);
        setShowMeetingRoom(true);

        setParticipants([{ id: Date.now(), name: '나 (방장)', role: 'host', isMe: true }]);
    };

    const handleJoinMeeting = () => {
        setShowMeetingCode(false);
        handleShareStart(); // Call handleShareStart to initiate the meeting room and participants
    };

    const handleCloseMeeting = () => {
        setShowMeetingRoom(false);
        setParticipants([{ id: 1, name: '나 (방장)', role: 'host', isMe: true }]); // Reset participants
    };

    const menuItems = [
        { id: 1, icon: <Home size={24} />, label: '홈', onClick: onHome || (() => navigate('/C/mall')) }, // onHome은 그대로 유지
        { id: 2, icon: <ShoppingCart size={24} />, label: '장바구니', onClick: () => navigate('/C/mypage/cart') }, // 장바구니 경로 변경
        { id: 3, icon: <User size={24} />, label: '마이페이지', onClick: onMyPage || (() => navigate('/C/mypage/orders')) }, // 마이페이지 링크를 /C/mypage/orders로 변경
        { id: 4, icon: <Share2 size={24} />, label: '공유하기', onClick: handleShareButtonClick, highlight: true },
    ];

    return (
        <div className="store-browser-container">
            {/* 실제 쇼핑몰 웹사이트 영역 */}
            <div className="iframe-wrapper">
                <iframe
                    src={mallUrl}
                    className="store-iframe"
                    title={`${mallName} 쇼핑몰`}
                    allow="fullscreen"
                />
            </div>

            {/* 고정 뒤로가기 버튼 */}
            {!showMeetingRoom && (
                <button onClick={onBack || (() => navigate(-1))} className="back-button-circle-c cursor-pointer" aria-label="뒤로가기">
                    <ArrowLeft size={24} />
                </button>
            )}

            {/* 화면 공유 UI (이미지 기반 3영역 분할) */}
            <AnimatePresence>
                {showMeetingRoom && (
                    <>
                        {/* 1. 상단 정보 바 (Top Center) */}
                        <motion.div
                            initial={{ y: -50, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: -50, opacity: 0 }}
                            className="top-sharing-info-c"
                        >
                            <div className="status-dot-c" />
                            <span className="info-text-c">화면 공유 중 <span className="divider-c">|</span> 초대 코드: <strong>{meetingCode}</strong></span>
                        </motion.div>

                        {/* 2. 하단 액션 바 (Bottom Center) */}
                        <motion.div
                            initial={{ y: 50, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: 50, opacity: 0 }}
                            className="bottom-sharing-actions-c"
                        >
                            <button onClick={() => setShowCart(true)} className="share-action-btn-c white-btn cursor-pointer">
                                <ShoppingCart size={20} /> 장바구니
                            </button>
                            <button onClick={handleCloseMeeting} className="share-action-btn-c purple-btn cursor-pointer">
                                <X size={20} /> 공유 종료
                            </button>
                        </motion.div>

                        {/* 3. 우측 참가자 패널 (Top Right) */}
                        <motion.div
                            initial={{ x: 50, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: 50, opacity: 0 }}
                            className="participants-panel-c"
                        >
                            <div className="panel-header-c">참가자 ({participants.length}명)</div>
                            <div className="participant-list-c">
                                <AnimatePresence>
                                    {participants.map((person) => (
                                        <motion.div
                                            key={person.id}
                                            initial={{ opacity: 0, x: 20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            className="participant-item-c"
                                        >
                                            <div className="user-avatar-c"><User size={18} /></div>
                                            <span className="user-name-c">{person.name}</span>
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                                {participants.length === 1 && (
                                    <div className="participant-item-c waiting">
                                        <div className="user-avatar-c"><User size={18} /></div>
                                        <span className="user-name-c">대기 중...</span>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* 플로팅 메뉴 버튼 영역 (이미지 기반 좌측 하단 디자인) */}
            {!showMeetingRoom && (
                <div className="floating-menu-wrapper-left">
                    <AnimatePresence>
                        {showMainMenu && (
                            <motion.div
                                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 20, scale: 0.95 }}
                                transition={{ type: "spring", damping: 20, stiffness: 300 }}
                                className="menu-panel-c"
                            >
                                {menuItems.map((item) => (
                                    <button
                                        key={item.id}
                                        className="menu-panel-item-c cursor-pointer"
                                        onClick={() => { item.onClick(); setShowMainMenu(false); }}
                                    >
                                        <div className="item-icon-c">{item.icon}</div>
                                        <span className="item-label-c">{item.label}</span>
                                    </button>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setShowMainMenu(!showMainMenu)}
                        className={`menu-toggle-btn-c cursor-pointer ${showMainMenu ? 'active' : ''}`}
                    >
                        {showMainMenu ? <X size={30} /> : <Menu size={30} />}
                    </motion.button>
                </div>
            )}

            {/* 초대 코드 팝업 모달 */}
            <AnimatePresence>
                {showMeetingCode && (
                    <div className="modal-overlay">
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            className="share-modal"
                        >
                            <h2 className="modal-title">초대 코드</h2>
                            <div className="code-box">
                                <span className="code-text">{meetingCode}</span>
                            </div>
                            <p className="modal-info">이 코드를 상대방에게 알려주세요.</p>
                            <div className="modal-btns">
                                <button onClick={() => setShowMeetingCode(false)} className="btn-close cursor-pointer">취소</button>
                                <button onClick={handleJoinMeeting} className="btn-confirm cursor-pointer">입장하기</button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* 페이지 전환 컴포넌트 */}
            {showCart && (
                <div className="full-screen-overlay">
                    <CartC onClose={() => setShowCart(false)} onHome={onHome} />
                </div>
            )}
            {showMyPage && (
                <div className="full-screen-overlay">
                    <MyPageC onBack={() => setShowMyPage(false)} onHome={onHome} onCart={() => { setShowMyPage(false); setShowCart(true); }} />
                </div>
            )}
        </div>
    );
};

export default StoreBrowserC;
