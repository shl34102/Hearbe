import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Fingerprint,
    Camera,
    X,
    ChevronRight,
    CreditCard,
    ArrowLeft
} from 'lucide-react';
import Swal from 'sweetalert2';
import logo from '../../assets/logoA.png';
import iconCamera from '../../assets/icon-camera.png';
import { authAPI } from '../../services/authAPI';
import './FindIdB.css';

const FindIdB = () => {
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

    const handleSubmitFindId = async () => {
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

        // 유효기간 MM/YY 형식 검증
        if (!/^(0[1-9]|1[0-2])\/[0-9]{2}$/.test(cardForm.expiration_date.trim())) {
            Swal.fire({
                icon: 'warning',
                text: '유효기간은 MM/YY 형식이어야 합니다. (예: 01/28)',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }

        // CVC 3~5자리 숫자 검증
        if (!/^[0-9]{3,5}$/.test(cardForm.cvc.trim())) {
            Swal.fire({
                icon: 'warning',
                text: 'CVC는 3~5자리 숫자여야 합니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }

        try {
            const response = await authAPI.findIdByWelfareCard({
                card_company: cardForm.card_company.trim(),
                card_number: cardForm.card_number.trim(),
                expiration_date: cardForm.expiration_date.trim(),
                cvc: cardForm.cvc.trim()
            });

            if (response.code === 200 && response.data) {
                Swal.fire({
                    icon: 'success',
                    text: `아이디 찾기 성공: 귀하의 아이디는 ${response.data} 입니다.`,
                    background: '#141C29',
                    color: '#FFF064',
                    confirmButtonColor: '#FFF064',
                    confirmButtonText: '<span style="color:#141C29">확인</span>'
                });
                navigate('/B/login');
            } else {
                throw new Error('일치하는 회원 정보가 없습니다.');
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || '정보 확인 중 오류가 발생했습니다.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    return (
        <div className="findid-a-page-new">
            <main className="findid-a-content-new">
                <div className="findid-a-card-new">
                    <div className="findid-a-header-new">
                        <img
                            src={logo}
                            alt="Logo"
                            className="findid-logo-a-new cursor-pointer"
                            onClick={() => navigate('/main')}
                        />
                        <h1 className="findid-title-a-new">아이디 찾기</h1>
                        <p className="findid-subtitle-a-new">등록된 복지카드를 촬영하여 아이디를 찾을 수 있습니다.</p>
                    </div>

                    <div className="findid-trigger-box-a-new" onClick={handleOpen}>
                        <div className="trigger-icon-area-a-new">
                            <Camera size={80} color="#141C29" />
                        </div>
                        <div className="trigger-text-area-a-new">
                            <span className="trigger-main-text-a-new">복지카드 촬영하기</span>
                            <span className="trigger-sub-text-a-new">빛 반사에 유의하여 촬영해 주세요.</span>
                        </div>
                        <ChevronRight size={40} color="#FFF064" />
                    </div>

                    <div className="findid-footer-a-new">
                        <button className="back-to-login-a-new" onClick={() => navigate('/B/login')}>
                            <ArrowLeft size={24} /> 로그인 페이지로 돌아가기
                        </button>
                    </div>
                </div>
            </main>

            {showModal && (
                <div className="findid-modal-overlay-a-new" onClick={handleClose}>
                    <div className="findid-modal-box-a-new" onClick={(e) => e.stopPropagation()}>
                        <button className="modal-close-a-new" onClick={handleClose}><X size={48} /></button>

                        {modalStep === 'camera' ? (
                            <div className="camera-modal-content-a-new">
                                <h2 className="modal-title-a-new">카드 촬영</h2>
                                <p className="modal-subtitle-a-new">복지카드 앞면을 가이드 영역에 맞춰주세요.</p>
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
                                <h2 className="modal-title-a-new">카드 정보 확인</h2>
                                <p className="modal-subtitle-a-new">인식된 정보가 여권/신분증과 일치하는지 확인해 주세요.</p>
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
                                        <button className="modal-primary-btn-a-new" onClick={handleSubmitFindId}>아이디 찾기</button>
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

export default FindIdB;
