import { User, Mail, Check } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';
import './FindIdC.css';
import logoC from '../../assets/logoC.png';

import { authAPI } from '../../services/authAPI';
import { emailService } from '../../services/emailService';

const FindIdC = () => {
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [verificationCode, setVerificationCode] = useState('');
    const [isSent, setIsSent] = useState(false);
    const [isVerified, setIsVerified] = useState(false);
    const [showIdPopup, setShowIdPopup] = useState(false);
    const [foundUserId, setFoundUserId] = useState('');

    const handleSendVerification = async () => {
        if (!name || !email) {
            Swal.fire({
                icon: 'warning',
                text: '이름과 이메일 주소를 입력해주세요.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
            return;
        }
        try {
            await emailService.sendVerificationCode(email, name);
            setIsSent(true);
            Swal.fire({
                icon: 'success',
                text: '인증번호가 이메일로 전송되었습니다. (3분 내 입력)',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || '인증번호 전송에 실패했습니다.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
        }
    };

    const handleVerifyCode = () => {
        if (!verificationCode) {
            Swal.fire({
                icon: 'warning',
                text: '인증번호를 입력해주세요.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
            return;
        }
        try {
            emailService.verifyCode(email, verificationCode);
            setIsVerified(true);
            Swal.fire({
                icon: 'success',
                text: '인증이 완료되었습니다.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || '인증번호가 일치하지 않습니다.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
        }
    };

    const handleFindId = async () => {
        if (!isVerified) {
            Swal.fire({
                icon: 'warning',
                text: '먼저 이메일 인증을 완료해주세요.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
            return;
        }
        try {
            const response = await authAPI.findId(name, email);
            if (response.data && response.data.username) {
                setFoundUserId(response.data.username);
                setShowIdPopup(true);
            } else {
                Swal.fire({
                    icon: 'error',
                    text: '해당 정보로 가입된 아이디를 찾을 수 없습니다.',
                    confirmButtonColor: '#7c3aed',
                    confirmButtonText: '확인'
                });
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                text: error.message || '아이디 찾기에 실패했습니다.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
        }
    };

    return (
        <div className="find-id-container-c">


            <main className="find-id-main-c">
                <div className="find-id-card-c">
                    <div className="card-header-c">
                        <img
                            src={logoC}
                            alt="HearBe"
                            className="mini-logo-c"
                            style={{ cursor: 'pointer' }}
                            onClick={() => navigate('/main')}
                        />
                        <h1>아이디 찾기</h1>
                        <p>가입 시 등록한 정보로 아이디를 찾을 수 있습니다.</p>
                    </div>

                    <div className="form-section-c">
                        <div className="input-field-c">
                            <label>이름</label>
                            <div className="input-wrapper-c">
                                <User className="input-icon-c" />
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="이름을 입력하세요"
                                />
                            </div>
                        </div>

                        <div className="input-field-c">
                            <label>이메일</label>
                            <div className="flex-row-c gap-2-c">
                                <div className="input-wrapper-c grow">
                                    <Mail className="input-icon-c" />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="example@mail.com"
                                    />
                                </div>
                                <button onClick={handleSendVerification} className="secondary-btn-c cursor-pointer">
                                    {isSent ? '재전송' : '인증요청'}
                                </button>
                            </div>
                        </div>

                        {isSent && (
                            <div className="input-field-c animate-slide-down-c">
                                <label>인증번호</label>
                                <div className="flex-row-c gap-2-c">
                                    <input
                                        type="text"
                                        value={verificationCode}
                                        onChange={(e) => setVerificationCode(e.target.value)}
                                        placeholder="6자리 숫자 입력"
                                        className="grow code-input-c"
                                    />
                                    <button onClick={handleVerifyCode} className="black-btn-c cursor-pointer">
                                        확인
                                    </button>
                                </div>
                            </div>
                        )}

                        <button
                            onClick={handleFindId}
                            className="submit-full-btn-c active cursor-pointer"
                        >
                            아이디 확인하기
                        </button>

                    </div>
                </div>
            </main>



            {showIdPopup && (
                <div className="modal-overlay-c">
                    <div className="id-result-modal-c">
                        <div className="check-icon-wrapper-c">
                            <Check className="check-icon-c" />
                        </div>
                        <h2 className="modal-title-c">아이디 조회 결과</h2>
                        <div className="result-box-c">
                            <span className="result-label-c">회원님의 아이디는</span>
                            <strong className="result-value-c">{foundUserId}</strong>
                        </div>
                        <button onClick={() => navigate('/C/login')} className="modal-confirm-btn-c cursor-pointer">
                            확인 및 로그인하기
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FindIdC;
