import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Lock,
    Camera,
    X,
    ChevronRight,
    CreditCard,
    ArrowLeft,
    ShieldCheck
} from 'lucide-react';
import Swal from 'sweetalert2';
import logo from '../../assets/logoA.png';
import iconCamera from '../../assets/icon-camera.png';
import { authAPI } from '../../services/authAPI';
import './FindPasswordB.css';

const FindPasswordB = () => {
    const navigate = useNavigate();
    const [showModal, setShowModal] = useState(false);
    const [modalStep, setModalStep] = useState('camera'); // camera | form
    const [cardForm, setCardForm] = useState({
        card_company: '',
        card_number: '',
        expiration_date: '',
        cvc: ''
    });
    const videoRef = useRef(null);
    const [stream, setStream] = useState(null);
    const [cameraError, setCameraError] = useState('');

    const handleOpen = () => {
        setModalStep('camera');
        setShowModal(true);
    };

    const handleClose = () => {
        setShowModal(false);
        stopCamera();
    };

    const handleSnap = () => {
        setCardForm({ card_company: '', card_number: '', expiration_date: '', cvc: '' });
        setModalStep('form');
    };

    const startCamera = async () => {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('이 브라우저에서 카메라를 사용할 수 없습니다.');
            }
            const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
            setStream(mediaStream);
            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
            }
            setCameraError('');
        } catch (err) {
            console.error('Error accessing camera:', err);
            setCameraError('카메라 접근이 차단되었습니다. 브라우저 권한을 확인해주세요.');
        }
    };

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach((track) => track.stop());
            setStream(null);
        }
    };

    useEffect(() => {
        if (showModal && modalStep === 'camera') {
            startCamera();
        } else {
            stopCamera();
        }
        return () => stopCamera();
    }, [showModal, modalStep]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        if (name === 'card_number') {
            const digits = value.replace(/[^0-9]/g, '').slice(0, 16);
            const formatted = digits.match(/.{1,4}/g)?.join('-') || digits;
            setCardForm((prev) => ({ ...prev, [name]: formatted }));
            return;
        }
        setCardForm((prev) => ({ ...prev, [name]: value }));
    };

    const handleVerify = async () => {
        if (!cardForm.card_company || !cardForm.card_number || !cardForm.expiration_date || !cardForm.cvc) {
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
        try {
            const verifyResponse = await authAPI.verifyWelfareCard({
                card_company: cardForm.card_company.trim(),
                card_number: cardForm.card_number.trim(),
                expiration_date: cardForm.expiration_date.trim(),
                cvc: cardForm.cvc.trim()
            });
            const isVerified = verifyResponse?.code === 200;
            if (!isVerified) {
                throw new Error('해당 정보가 없습니다.');
            }

            Swal.fire({
                icon: 'success',
                text: '인증 완료. 비밀번호 재설정 페이지로 이동합니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });

            localStorage.setItem('welfare_verified', 'true');
            localStorage.setItem('welfare_card', JSON.stringify({
                card_company: cardForm.card_company.trim(),
                card_number: cardForm.card_number.trim(),
                expiration_date: cardForm.expiration_date.trim(),
                cvc: cardForm.cvc.trim()
            }));

            setShowModal(false);
            navigate('/B/changePassword');

        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || '인증에 실패했습니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    return (
        <div className="findpw-a-page-new">
            <main className="findpw-a-content-new">
                <div className="findpw-a-card-new">
                    <div className="findpw-a-header-new">
                        <img
                            src={logo}
                            alt="Logo"
                            className="findpw-logo-a-new cursor-pointer"
                            onClick={() => navigate('/main')}
                        />
                        <h1 className="findpw-title-a-new">비밀번호 재설정</h1>
                        <p className="findpw-subtitle-a-new">안전한 서비스 이용을 위해 복지카드 촬영을 통한 본인 인증이 필요합니다.</p>
                    </div>

                    <div className="findpw-trigger-box-a-new" onClick={handleOpen}>
                        <div className="trigger-icon-area-a-new">
                            <ShieldCheck size={80} color="#141C29" />
                        </div>
                        <div className="trigger-text-area-a-new">
                            <span className="trigger-main-text-a-new">복지카드 촬영하기</span>
                            <span className="trigger-sub-text-a-new">인증 후 비밀번호를 재설정할 수 있습니다.</span>
                        </div>
                        <ChevronRight size={40} color="#FFF064" />
                    </div>

                    <div className="findpw-footer-a-new">
                        <button className="back-to-login-a-new" onClick={() => navigate('/B/login')}>
                            <ArrowLeft size={24} /> 로그인 페이지로 돌아가기
                        </button>
                    </div>
                </div>
            </main>

            {showModal && (
                <div className="findpw-modal-overlay-a-new" onClick={handleClose}>
                    <div className="findpw-modal-box-a-new" onClick={(e) => e.stopPropagation()}>
                        <button className="modal-close-a-new" onClick={handleClose}><X size={48} /></button>

                        {modalStep === 'camera' ? (
                            <div className="camera-modal-content-a-new">
                                <h2 className="modal-title-a-new">카드 촬영</h2>
                                <p className="modal-subtitle-a-new">복지카드를 수평에 맞춰 촬영해 주세요.</p>
                                <div className="camera-view-a-new">
                                    {stream ? (
                                        <video ref={videoRef} autoPlay playsInline muted />
                                    ) : (
                                        <div className="camera-placeholder-a-new">
                                            {cameraError || '카메라를 준비 중입니다...'}
                                        </div>
                                    )}
                                    <div className="camera-guide-a-new" />
                                </div>
                                {stream && (
                                    <button className="shutter-btn-a-new" onClick={handleSnap}>
                                        <div className="shutter-inner-a-new" />
                                    </button>
                                )}
                            </div>
                        ) : (
                            <div className="form-modal-content-a-new">
                                <h2 className="modal-title-a-new">카드 정보 인증</h2>
                                <p className="modal-subtitle-a-new">인식된 정보가 정확한지 확인 후 인증하기를 눌러주세요.</p>
                                <div className="modal-form-a-new">
                                    <div className="modal-input-group-a-new">
                                        <label>카드사</label>
                                        <input
                                            type="text"
                                            name="card_company"
                                            value={cardForm.card_company}
                                            onChange={handleInputChange}
                                        />
                                    </div>
                                    <div className="modal-input-group-a-new">
                                        <label>카드번호</label>
                                        <input
                                            type="text"
                                            name="card_number"
                                            value={cardForm.card_number}
                                            onChange={handleInputChange}
                                        />
                                    </div>
                                    <div className="modal-input-row-a-new">
                                        <div className="modal-input-group-a-new half">
                                            <label>유효기간</label>
                                            <input
                                                type="text"
                                                name="expiration_date"
                                                value={cardForm.expiration_date}
                                                onChange={handleInputChange}
                                                placeholder="MM/YY"
                                            />
                                        </div>
                                        <div className="modal-input-group-a-new half">
                                            <label>CVC</label>
                                            <input
                                                type="text"
                                                name="cvc"
                                                value={cardForm.cvc}
                                                onChange={handleInputChange}
                                                maxLength={3}
                                            />
                                        </div>
                                    </div>
                                    <div className="modal-btn-group-a-new">
                                        <button className="modal-secondary-btn-a-new" onClick={() => setModalStep('camera')}>다시 촬영</button>
                                        <button className="modal-primary-btn-a-new" onClick={handleVerify}>인증하기</button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default FindPasswordB;
