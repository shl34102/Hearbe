import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, X, ChevronRight, CreditCard } from 'lucide-react';
import logoA from '../../assets/logoA.png';
import Swal from 'sweetalert2';
import { authAPI } from '../../services/authAPI';
import './ChangePasswordB.css';
import './FindPasswordB.css';

const swalStyle = {
    background: '#141C29',
    color: '#FFF064',
    confirmButtonColor: '#FFF064',
    confirmButtonText: '<span style="color:#141C29">확인</span>'
};

const ChangePasswordB = () => {
    const navigate = useNavigate();
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const [showModal, setShowModal] = useState(false);
    const [modalStep, setModalStep] = useState('camera');
    const [cardForm, setCardForm] = useState({
        cardCompany: '',
        cardNumber: '',
        issueDate: '',
        expirationDate: '',
        cvc: ''
    });
    const [cardData, setCardData] = useState(null);

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
            console.error('Error accessing camera:', err);
        }
    };

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
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

    const handleSnap = () => {
        setCardForm({
            cardCompany: '신한카드',
            cardNumber: '0000-0000-0000-0000',
            issueDate: '2024-01-01',
            expirationDate: '01/30',
            cvc: '123'
        });
        setModalStep('form');
    };

    const handleCardInputChange = (e) => {
        const { name, value } = e.target;
        setCardForm(prev => ({ ...prev, [name]: value }));
    };

    const handleCardRegister = () => {
        if (!cardForm.cardCompany || !cardForm.cardNumber || !cardForm.expirationDate || !cardForm.cvc) {
            Swal.fire({ icon: 'warning', text: '복지카드 정보를 모두 입력해주세요.', ...swalStyle });
            return;
        }
        setCardData({ ...cardForm });
        setShowModal(false);
        setModalStep('camera');
        Swal.fire({ icon: 'success', text: '복지카드가 등록되었습니다.', ...swalStyle });
    };

    const handleSubmit = async () => {
        if (!cardData) {
            Swal.fire({ icon: 'warning', text: '복지카드를 먼저 촬영해주세요.', ...swalStyle });
            return;
        }
        if (!password || !confirmPassword) {
            Swal.fire({ icon: 'warning', text: '비밀번호를 입력해주세요.', ...swalStyle });
            return;
        }
        if (password.length !== 6 || confirmPassword.length !== 6) {
            Swal.fire({ icon: 'warning', text: '비밀번호는 숫자 6자리여야 합니다.', ...swalStyle });
            return;
        }
        if (password !== confirmPassword) {
            Swal.fire({ icon: 'warning', text: '비밀번호가 일치하지 않습니다.', ...swalStyle });
            return;
        }
        try {
            const welfareCard = {
                card_company: cardData.cardCompany.trim(),
                card_number: cardData.cardNumber.trim(),
                issue_date: cardData.issueDate.trim(),
                expiration_date: cardData.expirationDate.trim(),
                cvc: cardData.cvc.trim()
            };
            const response = await authAPI.resetPasswordBlind(welfareCard, password);
            if (response?.result === 'success') {
                Swal.fire({ icon: 'success', text: '비밀번호가 변경되었습니다.', ...swalStyle });
                navigate('/B/login');
                return;
            }
            Swal.fire({ icon: 'error', text: response?.message || '비밀번호 변경에 실패했습니다.', ...swalStyle });
        } catch (error) {
            Swal.fire({ icon: 'error', text: error.message || '비밀번호 변경에 실패했습니다.', ...swalStyle });
        }
    };

    return (
        <div className="changepw-a-page-new">
            <img
                src={logoA}
                alt="Logo"
                className="change-pw-logo"
                onClick={() => navigate('/main')}
            />
            <div className="change-pw-card">
                <h1 className="change-pw-title">비밀번호 변경</h1>
                <p className="change-pw-desc">복지카드 인증 후 새 비밀번호를 설정하세요.</p>

                <div className="change-pw-field">
                    <label>새 비밀번호(숫자 6자리)</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                        className="change-pw-input"
                    />
                </div>
                <div className="change-pw-field">
                    <label>비밀번호 확인</label>
                    <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                        className="change-pw-input"
                    />
                </div>

                <div className="change-pw-card-section">
                    <label className="change-pw-field-label">복지카드 인증</label>
                    {cardData ? (
                        <div className="change-pw-card-registered" onClick={() => setShowModal(true)}>
                            <CreditCard size={32} color="#FFF064" />
                            <div className="change-pw-card-info">
                                <span>{cardData.cardCompany}</span>
                                <span>{cardData.cardNumber.replace(/\d(?=\d{4})/g, '*')}</span>
                            </div>
                            <ChevronRight size={24} color="#FFF064" />
                        </div>
                    ) : (
                        <div className="change-pw-card-trigger" onClick={() => setShowModal(true)}>
                            <Camera size={40} />
                            <span>복지카드 촬영하기</span>
                        </div>
                    )}
                </div>

                <button className="change-pw-btn" onClick={handleSubmit}>
                    비밀번호 변경하기
                </button>
            </div>

            {showModal && (
                <div className="findpw-modal-overlay-a-new" onClick={() => setShowModal(false)}>
                    <div className="findpw-modal-box-a-new" onClick={(e) => e.stopPropagation()}>
                        <button className="modal-close-a-new" onClick={() => setShowModal(false)}><X size={48} /></button>

                        {modalStep === 'camera' ? (
                            <div className="camera-modal-content-a-new">
                                <h2 className="modal-title-a-new">카드 촬영</h2>
                                <p className="modal-subtitle-a-new">복지카드를 수평에 맞춰 촬영해 주세요.</p>
                                <div className="camera-view-a-new">
                                    {stream ? (
                                        <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '20px' }} />
                                    ) : (
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#FFF064', fontSize: '20px' }}>
                                            카메라를 준비 중입니다...
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
                                <p className="modal-subtitle-a-new">인식된 정보가 정확한지 확인 후 등록하기를 눌러주세요.</p>
                                <div className="modal-form-a-new">
                                    <div className="modal-input-group-a-new">
                                        <label>카드사</label>
                                        <input type="text" name="cardCompany" value={cardForm.cardCompany} onChange={handleCardInputChange} />
                                    </div>
                                    <div className="modal-input-group-a-new">
                                        <label>카드번호</label>
                                        <input type="text" name="cardNumber" value={cardForm.cardNumber} onChange={handleCardInputChange} />
                                    </div>
                                    <div className="modal-input-row-a-new">
                                        <div className="modal-input-group-a-new half">
                                            <label>유효기간</label>
                                            <input type="text" name="expirationDate" value={cardForm.expirationDate} onChange={handleCardInputChange} placeholder="MM/YY" />
                                        </div>
                                        <div className="modal-input-group-a-new half">
                                            <label>CVC</label>
                                            <input type="text" name="cvc" value={cardForm.cvc} onChange={handleCardInputChange} maxLength={3} />
                                        </div>
                                    </div>
                                    <div className="modal-btn-group-a-new">
                                        <button className="modal-secondary-btn-a-new" onClick={() => setModalStep('camera')}>다시 촬영</button>
                                        <button className="modal-primary-btn-a-new" onClick={handleCardRegister}>등록하기</button>
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

export default ChangePasswordB;
