import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import { usePeerView } from '../../hooks/peerjs/usePeerView';
import GuardianJoinModal from '../../components/ShareCode/GuardianJoinModal';
import logoC from '../../assets/logoC.png';
import './GuardianViewS.css';

const GuardianViewS = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const videoRef = useRef(null);
    const [activeCode, setActiveCode] = useState(null);
    const [showJoinModal, setShowJoinModal] = useState(false);

    const { remoteStream, isConnected, error, joinSession, leave } = usePeerView();

    useEffect(() => {
        const stateCode = location.state?.code;
        const searchParams = new URLSearchParams(location.search);
        const queryCode = searchParams.get('code');
        const code = stateCode || queryCode;

        if (code) {
            handleJoinSession(code);
        } else {
            setShowJoinModal(true);
        }

        return () => {
            leave();
        };
    }, []);

    const handleJoinSession = (code) => {
        setActiveCode(code);
        setShowJoinModal(false);

        joinSession(code).catch((err) => {
            console.error('세션 입장 실패:', err);
            // alert(`연결 실패: ${err.message}`);
        });
    };

    const handleManualJoin = (code) => {
        handleJoinSession(code);
    };

    useEffect(() => {
        if (remoteStream && videoRef.current) {
            videoRef.current.srcObject = remoteStream;
        }
    }, [remoteStream]);

    const handleLeave = () => {
        leave();
        navigate('/main');
    };

    return (
        <div className="guardian-view-container">
            <header className="guardian-header-c">
                <div className="header-left-c">
                    <img
                        src={logoC}
                        alt="HearBe Logo"
                        className="header-logo-c"
                        onClick={() => navigate('/main')}
                        style={{ height: '50px', cursor: 'pointer', objectFit: 'contain' }}
                    />
                    <span className="header-title-c">실시간 화면 공유</span>
                </div>
                <button className="leave-button-c cursor-pointer" onClick={handleLeave}>
                    <LogOut size={18} />
                    <span>연결 종료</span>
                </button>
            </header>

            <div className="video-container">
                {!isConnected && (
                    <div className="loading-overlay">
                        <div className="loading-spinner"></div>
                        <p>{activeCode ? '사용자 화면 연결 중...' : '코드를 입력해주세요'}</p>
                    </div>
                )}
                <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    className="remote-video"
                />
            </div>

            {error && (
                <div className="error-banner">
                    ⚠️ {error}
                </div>
            )}

            <div className="status-bar">
                <span className={`status-indicator ${isConnected ? 'connected' : 'connecting'}`}></span>
                <span className="status-text">
                    {isConnected ? '연결됨' : '연결 중...'}
                </span>
                <span className="code-badge">코드: {activeCode || '----'}</span>
            </div>

            <GuardianJoinModal
                isOpen={showJoinModal}
                onClose={() => navigate('/main')}
                onJoin={handleManualJoin}
            />
        </div>
    );
};

export default GuardianViewS;
