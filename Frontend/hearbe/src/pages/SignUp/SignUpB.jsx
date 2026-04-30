import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    User,
    Lock,
    Smartphone,
    Camera,
    Upload,
    CreditCard,
    Check,
    ChevronRight,
    X,
    Eye,
    EyeOff,
    LoaderCircle
} from 'lucide-react';
import Swal from 'sweetalert2';
import logo from '../../assets/logoA.png';
import { authAPI } from '../../services/authAPI';
import { validateUsername } from '../../utils/validation';
import './SignUpB.css';

// Utility Functions
const formatPhoneNumber = (value) => {
    const numbers = value.replace(/[^\d]/g, '');
    const limited = numbers.slice(0, 11);
    if (limited.length <= 3) return limited;
    if (limited.length <= 7) return `${limited.slice(0, 3)}-${limited.slice(3)}`;
    return `${limited.slice(0, 3)}-${limited.slice(3, 7)}-${limited.slice(7)}`;
};

const validatePassword = (password) => /^\d{6}$/.test(password);
const OCR_LOW_CONFIDENCE_THRESHOLD = 0.8;
const OCR_MAX_FILE_SIZE = 20 * 1024 * 1024;

const formatCardNumber = (value) => {
    const digits = value.replace(/[^\d]/g, '').slice(0, 16);
    const groups = digits.match(/.{1,4}/g);
    return groups ? groups.join('-') : '';
};

const formatExpiry = (value) => {
    const digits = value.replace(/[^\d]/g, '').slice(0, 4);
    if (digits.length <= 2) return digits;
    return `${digits.slice(0, 2)}/${digits.slice(2)}`;
};

const normalizeExpiry = (value) => {
    if (!value) return '';
    const trimmed = value.trim();
    if (!trimmed) return '';

    if (/^\d{2}\/\d{2}$/.test(trimmed)) {
        return trimmed;
    }

    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
        const [year, month] = trimmed.split('-');
        return `${month}/${year.slice(-2)}`;
    }

    if (/^\d{2}-\d{2}$/.test(trimmed)) {
        return trimmed.replace('-', '/');
    }

    return formatExpiry(trimmed);
};

const FIELD_LABELS = {
    company: '카드사',
    number: '카드번호',
    expiry: '유효기간',
    cvc: 'CVC'
};

const SignUpB = () => {
    const navigate = useNavigate();


    const [formData, setFormData] = useState({
        id: '',
        password: '',
        name: '',
        phone: ''
    });

    const [showPassword, setShowPassword] = useState(false);
    const [isIdChecked, setIsIdChecked] = useState(false);
    const [isIdAvailable, setIsIdAvailable] = useState(false);


    const [terms, setTerms] = useState({
        term1: false,
        term2: false,
    });


    const [showCamera, setShowCamera] = useState(false);
    const [modalStep, setModalStep] = useState('camera'); // 'camera' or 'form'
    const [cardData, setCardData] = useState(null);
    const [cardForm, setCardForm] = useState({
        company: '',
        number: '',
        expiry: '',
        cvc: ''
    });
    const [isOcrLoading, setIsOcrLoading] = useState(false);
    const [lowConfidenceFields, setLowConfidenceFields] = useState([]);


    const [showTermsModal, setShowTermsModal] = useState(false);


    const videoRef = useRef(null);
    const fileInputRef = useRef(null);
    const [stream, setStream] = useState(null);

    const openCardModal = () => {
        setShowCamera(true);
        setModalStep('camera');
        setLowConfidenceFields([]);
    };

    const closeCardModal = () => {
        setShowCamera(false);
        setModalStep('camera');
        setLowConfidenceFields([]);
    };

    const startCamera = async () => {
        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
            setStream(mediaStream);
            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
            }
        } catch (err) {
            console.error("Error accessing camera:", err);
            Swal.fire({
                icon: 'error',
                text: '카메라에 접근할 수 없습니다. 권한을 확인해주세요.',
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
    };

    useEffect(() => {
        if (showCamera && modalStep === 'camera') {
            startCamera();
        } else {
            stopCamera();
        }
        return () => stopCamera();
    }, [showCamera, modalStep]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        if (name === 'phone') {
            setFormData(prev => ({ ...prev, [name]: formatPhoneNumber(value) }));
        } else {
            setFormData(prev => ({ ...prev, [name]: value }));
        }

        if (name === 'id') {
            setIsIdChecked(false);
            setIsIdAvailable(false);
        }
    };

    const handleDuplicateCheck = async () => {
        const idError = validateUsername(formData.id);
        if (idError) {
            Swal.fire({
                icon: 'warning',
                text: idError,
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
            return;
        }

        try {
            const result = await authAPI.checkDuplicate(formData.id);
            const isDuplicate = result.data;
            if (isDuplicate === false) {
                setIsIdChecked(true);
                setIsIdAvailable(true);
                Swal.fire({
                    icon: 'success',
                    text: '사용 가능한 아이디입니다.',
                    background: '#141C29',
                    color: '#FFF064',
                    confirmButtonColor: '#FFF064',
                    confirmButtonText: '<span style="color:#141C29">확인</span>'
                });
            } else {
                setIsIdAvailable(false);
                Swal.fire({
                    icon: 'error',
                    text: '이미 사용 중인 아이디입니다.',
                    background: '#141C29',
                    color: '#FFF064',
                    confirmButtonColor: '#FFF064',
                    confirmButtonText: '<span style="color:#141C29">확인</span>'
                });
                setIsIdChecked(true);
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || "아이디 중복 확인에 실패했습니다.",
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    const captureFrameAsFile = () => new Promise((resolve, reject) => {
        const video = videoRef.current;
        if (!video || !video.videoWidth || !video.videoHeight) {
            reject(new Error('카메라 화면을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.'));
            return;
        }

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext('2d');
        if (!context) {
            reject(new Error('이미지 처리를 시작할 수 없습니다.'));
            return;
        }

        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
            if (!blob) {
                reject(new Error('촬영 이미지 생성에 실패했습니다.'));
                return;
            }

            const capturedFile = new File(
                [blob],
                `welfare-card-${Date.now()}.jpg`,
                { type: 'image/jpeg' }
            );
            resolve(capturedFile);
        }, 'image/jpeg', 0.92);
    });

    const applyOcrResultToForm = (ocrResult) => {
        const nextForm = {
            company: (ocrResult?.card_company || '').trim(),
            number: formatCardNumber(ocrResult?.card_number || ''),
            expiry: normalizeExpiry(ocrResult?.expiration_date || ''),
            cvc: (ocrResult?.cvc || '').replace(/[^\d]/g, '').slice(0, 3)
        };
        setCardForm(nextForm);

        const confidence = ocrResult?.confidence || {};
        const lowFields = Object.entries({
            company: confidence.card_company,
            number: confidence.card_number,
            expiry: confidence.expiration_date,
            cvc: confidence.cvc
        }).reduce((acc, [fieldName, score]) => {
            const hasValue = !!nextForm[fieldName];
            const isLowConfidence = score == null || score < OCR_LOW_CONFIDENCE_THRESHOLD;
            if (!hasValue || isLowConfidence) {
                acc.push(fieldName);
            }
            return acc;
        }, []);

        setLowConfidenceFields(lowFields);
        return lowFields;
    };

    const runWelfareCardOcr = async (file) => {
        if (!file) return;
        if (file.size > OCR_MAX_FILE_SIZE) {
            Swal.fire({
                icon: 'warning',
                text: '이미지 파일은 최대 20MB까지 업로드할 수 있습니다.',
                confirmButtonText: '확인'
            });
            return;
        }

        setIsOcrLoading(true);
        try {
            const ocrResult = await authAPI.ocrWelfareCard(file);
            const lowFields = applyOcrResultToForm(ocrResult);
            setModalStep('form');

            if (lowFields.length > 0) {
                const lowFieldLabels = lowFields.map((field) => FIELD_LABELS[field]).join(', ');
                Swal.fire({
                    icon: 'info',
                    text: `인식 신뢰도가 낮은 항목(${lowFieldLabels})이 있습니다. 직접 확인 후 수정해주세요.`,
                    confirmButtonText: '확인'
                });
            }
        } catch (error) {
            setModalStep('form');
            setLowConfidenceFields(['company', 'number', 'expiry', 'cvc']);
            Swal.fire({
                icon: 'warning',
                text: error.message || '카드 OCR 인식에 실패했습니다. 정보를 직접 입력해주세요.',
                confirmButtonText: '확인'
            });
        } finally {
            setIsOcrLoading(false);
        }
    };

    const handleSnap = async () => {
        try {
            const capturedFile = await captureFrameAsFile();
            await runWelfareCardOcr(capturedFile);
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || '카드 촬영에 실패했습니다.',
                confirmButtonText: '확인'
            });
        }
    };

    const handleFilePick = () => {
        fileInputRef.current?.click();
    };

    const handleFileSelect = async (e) => {
        const selectedFile = e.target.files?.[0];
        e.target.value = '';
        await runWelfareCardOcr(selectedFile);
    };

    const handleCardFormChange = (e) => {
        const { name, value } = e.target;
        setCardForm((prev) => {
            if (name === 'number') {
                return { ...prev, number: formatCardNumber(value) };
            }
            if (name === 'expiry') {
                return { ...prev, expiry: formatExpiry(value) };
            }
            if (name === 'cvc') {
                return { ...prev, cvc: value.replace(/[^\d]/g, '').slice(0, 3) };
            }
            return { ...prev, [name]: value };
        });

        setLowConfidenceFields((prev) => prev.filter((field) => field !== name));
    };

    const handleCardRegister = () => {
        if (!cardForm.company || !cardForm.number || !cardForm.expiry || !cardForm.cvc) {
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

        const today = new Date();
        const issueDate = today.toISOString().split('T')[0];
        setCardData({
            company: cardForm.company.trim(),
            number: formatCardNumber(cardForm.number),
            expiry: normalizeExpiry(cardForm.expiry),
            cvc: cardForm.cvc,
            issueDate
        });
        closeCardModal();
        Swal.fire({
            icon: 'success',
            text: '복지카드가 등록되었습니다.',
            background: '#141C29',
            color: '#FFF064',
            confirmButtonColor: '#FFF064',
            confirmButtonText: '<span style="color:#141C29">확인</span>'
        });
    };

    const handleSignUp = async () => {
        if (!isIdChecked || !isIdAvailable) {
            Swal.fire({ icon: 'warning', text: '아이디 중복 확인이 필요합니다.', background: '#141C29', color: '#FFF064', confirmButtonColor: '#FFF064', confirmButtonText: '<span style="color:#141C29">확인</span>' });
            return;
        }
        if (!validatePassword(formData.password)) {
            Swal.fire({ icon: 'warning', text: '비밀번호는 숫자 6자리를 입력해주세요.', background: '#141C29', color: '#FFF064', confirmButtonColor: '#FFF064', confirmButtonText: '<span style="color:#141C29">확인</span>' });
            return;
        }
        if (!formData.name) {
            Swal.fire({ icon: 'warning', text: '이름을 입력해주세요.', background: '#141C29', color: '#FFF064', confirmButtonColor: '#FFF064', confirmButtonText: '<span style="color:#141C29">확인</span>' });
            return;
        }
        if (!cardData) {
            Swal.fire({ icon: 'warning', text: '장애인 복지카드를 등록해주세요.', background: '#141C29', color: '#FFF064', confirmButtonColor: '#FFF064', confirmButtonText: '<span style="color:#141C29">확인</span>' });
            return;
        }
        if (!terms.term1 || !terms.term2) {
            Swal.fire({ icon: 'warning', text: '필수 이용약관에 동의해주세요.', background: '#141C29', color: '#FFF064', confirmButtonColor: '#FFF064', confirmButtonText: '<span style="color:#141C29">확인</span>' });
            return;
        }

        try {
            const userData = {
                username: formData.id,
                name: formData.name,
                email: `${formData.id}@hearbe.com`,
                phone_number: formData.phone,
                user_type: "BLIND",
                simple_password: formData.password,
                welfare_card: {
                    card_company: cardData.company,
                    card_number: cardData.number,
                    issue_date: cardData.issueDate,
                    expiration_date: cardData.expiry,
                    cvc: cardData.cvc
                }
            };

            const response = await authAPI.register(userData);
            if (response.success) {
                Swal.fire({
                    icon: 'success',
                    text: '가입 완료! HearBe 회원이 되신 것을 환영합니다.',
                    background: '#141C29',
                    color: '#FFF064',
                    confirmButtonColor: '#FFF064',
                    confirmButtonText: '<span style="color:#141C29">확인</span>'
                });
                navigate('/B/login');
            } else {
                throw new Error(response.message || '회원가입에 실패했습니다.');
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || "회원가입 중 오류가 발생했습니다.",
                background: '#141C29',
                color: '#FFF064',
                confirmButtonColor: '#FFF064',
                confirmButtonText: '<span style="color:#141C29">확인</span>'
            });
        }
    };

    return (
        <div className="signup-a-page-new">
            <main className="signup-a-content-new">
                <div className="signup-a-card-new">
                    <div className="signup-a-header-new">
                        <img
                            src={logo}
                            alt="Logo"
                            className="signup-logo-a-new cursor-pointer"
                            onClick={() => navigate('/main')}
                        />
                        <h1 className="signup-title-a-new">회원가입</h1>
                        <p className="signup-subtitle-a-new">나만을 위한 특별한 쇼핑 도우미, HearBe</p>
                    </div>

                    <div className="signup-a-form-new">
                        <div className="input-section-a-new">
                            <label className="input-label-a-new">아이디</label>
                            <div className="input-with-button-a-new">
                                <div className="input-icon-wrapper-a-new">
                                    <User size={32} />
                                    <input
                                        type="text"
                                        name="id"
                                        placeholder="영문, 숫자 포함 4자 이상"
                                        className="signup-input-a-new"
                                        value={formData.id}
                                        onChange={handleInputChange}
                                    />
                                </div>
                                <button
                                    className={`check-btn-a-new ${isIdChecked && isIdAvailable ? 'available' : ''}`}
                                    onClick={handleDuplicateCheck}
                                >
                                    {isIdChecked && isIdAvailable ? '확인됨' : '중복확인'}
                                </button>
                            </div>
                        </div>

                        <div className="input-section-a-new">
                            <label className="input-label-a-new">비밀번호 (숫자 6자리)</label>
                            <div className="input-icon-wrapper-a-new">
                                <Lock size={32} />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    name="password"
                                    placeholder="간편 비밀번호 6자리"
                                    className="signup-input-a-new"
                                    value={formData.password}
                                    onChange={handleInputChange}
                                    maxLength={6}
                                />
                                <button
                                    type="button"
                                    className="pw-toggle-a-new"
                                    onClick={() => setShowPassword(!showPassword)}
                                >
                                    {showPassword ? <EyeOff size={44} /> : <Eye size={44} />}
                                </button>
                            </div>
                        </div>

                        <div className="input-section-a-new">
                            <label className="input-label-a-new">이름</label>
                            <div className="input-icon-wrapper-a-new">
                                <User size={32} />
                                <input
                                    type="text"
                                    name="name"
                                    placeholder="성함을 입력해주세요"
                                    className="signup-input-a-new"
                                    value={formData.name}
                                    onChange={handleInputChange}
                                />
                            </div>
                        </div>

                        <div className="input-section-a-new">
                            <label className="input-label-a-new">휴대전화번호 (선택)</label>
                            <div className="input-icon-wrapper-a-new">
                                <Smartphone size={32} />
                                <input
                                    type="tel"
                                    name="phone"
                                    placeholder="010-0000-0000"
                                    className="signup-input-a-new"
                                    value={formData.phone}
                                    onChange={handleInputChange}
                                    maxLength={13}
                                />
                            </div>
                        </div>

                        <div className="input-section-a-new">
                            <label className="input-label-a-new">장애인 복지카드 등록</label>
                            {cardData ? (
                                <div className="card-info-box-a-new" onClick={openCardModal}>
                                    <div className="card-icon-wrapper-a-new">
                                        <CreditCard size={48} color="#FFF064" />
                                    </div>
                                    <div className="card-details-a-new">
                                        <span className="card-company-a-new">{cardData.company}</span>
                                        <span className="card-number-a-new">{cardData.number.replace(/\d(?=\d{4})/g, "*")}</span>
                                    </div>
                                    <ChevronRight size={32} color="#FFF064" />
                                </div>
                            ) : (
                                <div className="camera-trigger-a-new" onClick={openCardModal}>
                                    <Camera size={64} />
                                    <span>복지카드 촬영하기</span>
                                </div>
                            )}
                        </div>

                        <div className="terms-section-a-new">
                            <label className="terms-all-a-new">
                                <input
                                    type="checkbox"
                                    checked={terms.term1 && terms.term2}
                                    onChange={(e) => setTerms({ term1: e.target.checked, term2: e.target.checked })}
                                />
                                <span className="terms-checkmark-a-new">
                                    {(terms.term1 && terms.term2) && <Check size={44} strokeWidth={4} />}
                                </span>
                                <span className="terms-label-text-a-new">[필수] 이용약관 및 개인정보 동의</span>
                            </label>
                            <button className="terms-view-btn-a-new" onClick={() => setShowTermsModal(true)}>보기</button>
                        </div>

                        <button className="signup-submit-btn-a-new" onClick={handleSignUp}>
                            회원가입
                        </button>
                    </div>
                </div>
            </main>

            {showCamera && (
                <div className="signup-modal-overlay-a-new">
                    <div className="signup-modal-box-a-new">
                        <button className="modal-close-a-new" onClick={closeCardModal}><X size={48} /></button>

                        {modalStep === 'camera' ? (
                            <div className="camera-modal-content-a-new">
                                <h2 className="modal-title-a-new">카드 촬영</h2>
                                <p className="modal-subtitle-a-new">복지카드 앞면이 가이드 안에 들어오게 해주세요. (최대 20MB, OCR 최대 45초)</p>
                                <div className="camera-view-a-new">
                                    <video ref={videoRef} autoPlay playsInline muted />
                                    <div className="camera-guide-a-new" />
                                </div>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    className="ocr-file-input-a-new"
                                    onChange={handleFileSelect}
                                />
                                <button
                                    className="shutter-btn-a-new"
                                    onClick={handleSnap}
                                    disabled={isOcrLoading}
                                >
                                    <div className="shutter-inner-a-new" />
                                </button>
                                <button
                                    className="upload-btn-a-new"
                                    onClick={handleFilePick}
                                    disabled={isOcrLoading}
                                >
                                    <Upload size={24} />
                                    이미지 업로드
                                </button>
                                {isOcrLoading && (
                                    <p className="ocr-status-text-a-new">
                                        <LoaderCircle size={24} className="ocr-loading-icon-a-new" />
                                        카드 정보를 인식 중입니다. 잠시만 기다려주세요.
                                    </p>
                                )}
                            </div>
                        ) : (
                            <div className="form-modal-content-a-new">
                                <h2 className="modal-title-a-new">정보 확인</h2>
                                <p className="modal-subtitle-a-new">인식된 정보는 정확도 100%가 아닐 수 있습니다. 꼭 확인 후 수정해주세요.</p>
                                {lowConfidenceFields.length > 0 && (
                                    <div className="ocr-warning-box-a-new">
                                        신뢰도가 낮거나 비어 있는 항목:
                                        {` ${lowConfidenceFields.map((field) => FIELD_LABELS[field]).join(', ')}`}
                                    </div>
                                )}
                                <div className="modal-form-a-new">
                                    <div className="modal-input-group-a-new">
                                        <label className={lowConfidenceFields.includes('company') ? 'low-confidence-field-a-new' : ''}>카드사</label>
                                        <input type="text" name="company" value={cardForm.company} onChange={handleCardFormChange} />
                                    </div>
                                    <div className="modal-input-group-a-new">
                                        <label className={lowConfidenceFields.includes('number') ? 'low-confidence-field-a-new' : ''}>카드번호</label>
                                        <input type="text" name="number" value={cardForm.number} onChange={handleCardFormChange} />
                                    </div>
                                    <div className="modal-input-row-a-new">
                                        <div className="modal-input-group-a-new half">
                                            <label className={lowConfidenceFields.includes('expiry') ? 'low-confidence-field-a-new' : ''}>유효기간</label>
                                            <input type="text" name="expiry" value={cardForm.expiry} onChange={handleCardFormChange} placeholder="MM/YY" />
                                        </div>
                                        <div className="modal-input-group-a-new half">
                                            <label className={lowConfidenceFields.includes('cvc') ? 'low-confidence-field-a-new' : ''}>CVC</label>
                                            <input type="text" name="cvc" value={cardForm.cvc} onChange={handleCardFormChange} maxLength={3} />
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

            {showTermsModal && (
                <div className="signup-modal-overlay-a-new" onClick={() => setShowTermsModal(false)}>
                    <div className="terms-modal-box-a-new" onClick={(e) => e.stopPropagation()}>
                        <h2 className="terms-modal-title-a-new">이용약관 및 개인정보 수집 동의</h2>
                        <div className="terms-modal-content-area-a-new">
                            <h3 style={{ fontSize: '32px', marginBottom: '15px' }}>제1조 (AI 에이전트 서비스 이용 안내)</h3>
                            <p>
                                본 서비스는 사용자의 편리한 쇼핑을 위해 AI 에이전트 기술을 활용합니다.<br /><br />
                                <strong>AI 브라우저 대리 조작:</strong> 사용자가 음성으로 명령하면, HearBe의 AI 에이전트가 가상 브라우저를 통해 실제 쇼핑몰 웹사이트를 사용자를 대신하여 탐색하고 조작합니다. 이는 사용자가 직접 화면을 보고 클릭하는 과정을 AI가 음성 명령에 따라 수행하는 것입니다.<br /><br />
                                <strong>화면 분석 및 정보 제공:</strong> AI는 쇼핑몰의 이미지와 텍스트를 실시간으로 분석하여 사용자에게 음성으로 전달합니다. 이 과정에서 정확한 정보 전달을 위해 화면 캡처 및 텍스트 추출이 이루어질 수 있습니다.
                            </p>
                            <div style={{ borderBottom: '2px solid #141C29', margin: '30px 0' }}></div>
                            <h3 style={{ fontSize: '32px', marginBottom: '15px' }}>제2조 (개인정보 수집 및 이용 항목)</h3>
                            <p>
                                서비스 제공을 위해 아래와 같은 정보를 수집합니다. 수집된 정보는 회원 탈퇴 시 또는 법정 보유 기간 종료 시 즉시 파기됩니다.<br /><br />
                                <strong>1. 시각장애인 사용자 (A형·B형)</strong><br />
                                - 필수 수집 항목: 아이디, 비밀번호, 이름<br />
                                - 선택 수집 항목: 휴대폰 번호 <br />
                                - 장애인 복지 카드 확인 정보: 카드사, 카드번호 뒤 4자리, 유효기간 (사용자 맞춤형 UI 제공 목적)<br />
                                - 음성 데이터: 음성 명령 인식 및 처리 (목적 달성 후 즉시 파기)<br /><br />
                                <strong>2. 일반인 및 보호자 사용자 (C형)</strong><br />
                                - 필수 수집 항목: 아이디, 비밀번호, 이름, 이메일 주소<br />
                                - 원격 제어 정보: 사용자 브라우저 원격 조종을 위한 접속 로그 및 명령 데이터
                            </p>
                            <div style={{ borderBottom: '2px solid #141C29', margin: '30px 0' }}></div>
                            <h3 style={{ fontSize: '32px', marginBottom: '15px' }}>제3조 (결제 보안 및 민감 정보 보호)</h3>
                            <p>
                                <strong>결제 확인:</strong> AI가 사용자를 대신해 결제 단계까지 진입할 수 있으나, 실제 결제 승인은 사용자의 최종 확인(비밀번호 입력 또는 음성 확답)이 있어야만 완료됩니다.<br /><br />
                                <strong>비밀번호 미저장 원칙:</strong> 사용자의 결제 비밀번호는 서비스 내 어떠한 장치나 서버에도 저장되지 않으며, 결제 시마다 사용자가 직접 입력하는 것을 원칙으로 합니다.<br /><br />
                                <strong>기기 기반 암호화 등록:</strong> 복지 카드 정보 등 서비스 이용을 위해 등록한 민감 정보는 서버에 저장되지 않으며, 사용자가 서비스에 접속한 해당 웹 브라우저 및 기기에만 암호화되어 등록됩니다.<br /><br />
                                <strong>입력 단계 보안:</strong> 결제 관련 민감 정보 입력 시에는 AI의 화면 분석 기능을 일시 제한하며, 사용자의 기기 내에서 직접 암호화 처리를 수행하여 정보 유출을 원천 차단합니다.<br /><br />
                                <strong>데이터 비식별화:</strong> 음성 및 이미지 분석을 위해 외부 AI 엔진을 이용할 경우, 개인을 식별할 수 없는 데이터 형태로 가공하여 전송합니다.
                            </p>
                        </div>
                        <button className="terms-modal-confirm-btn-a-new" onClick={() => {
                            setTerms({ term1: true, term2: true });
                            setShowTermsModal(false);
                        }}>
                            동의하고 확인했습니다
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SignUpB;
