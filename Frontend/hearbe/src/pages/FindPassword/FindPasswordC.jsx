import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Mail, Lock, ShieldCheck, Smile, Eye, EyeOff } from 'lucide-react';
import Swal from 'sweetalert2';
import logoC from '../../assets/logoC.png';
import './FindPasswordC.css';

import { authAPI } from '../../services/authAPI';
import { emailService } from '../../services/emailService';

const FindPasswordC = ({ onBack }) => {
    const navigate = useNavigate();
    const goBack = onBack || (() => navigate('/C/login'));
    const [step, setStep] = useState(1);
    const [name, setName] = useState('');
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [verificationCode, setVerificationCode] = useState('');
    const [isSent, setIsSent] = useState(false);
    const [isVerified, setIsVerified] = useState(false);

    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const handleSendVerification = async () => {
        if (!name || !username || !email) {
            Swal.fire({
                icon: 'warning',
                text: '이름, 아이디, 그리고 이메일 주소를 모두 입력해주세요.',
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
                html: '본인 인증이 완료되었습니다.<br/>하단의 버튼을 눌러 비밀번호를 재설정해주세요.',
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

    const handleNextStep = () => {
        if (!isVerified) {
            Swal.fire({
                icon: 'warning',
                text: '먼저 이메일 인증을 완료해주세요.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
            return;
        }
        setStep(2);
    };

    const handleResetPassword = async (e) => {
        e.preventDefault();
        if (newPassword !== confirmPassword) {
            Swal.fire({
                icon: 'warning',
                text: '비밀번호가 일치하지 않습니다.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
            return;
        }
        try {
            await authAPI.resetPassword(email, newPassword);
            Swal.fire({
                icon: 'success',
                text: '비밀번호가 성공적으로 재설정되었습니다.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
            goBack();
        } catch (error) {
            // "데이터베이스 오류" 등 모호한 메시지가 올 경우, 기존 비밀번호와 동일할 가능성이 높음 (사용자 피드백 반영)
            let errorMessage = error.message;
            if (errorMessage && (errorMessage.includes('데이터베이스') || errorMessage.includes('Duplicate'))) {
                errorMessage = '현재 비밀번호와 동일합니다.<br/>다른 비밀번호를 입력해 주세요.';
            } else {
                errorMessage = errorMessage || '비밀번호 재설정에 실패했습니다.';
            }

            Swal.fire({
                icon: 'error',
                html: errorMessage,
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
        }
    };

    return (
        <div className="find-pw-container-c">


            <main className="find-pw-main-c">
                <div className="pw-form-card-c">
                    <div className="pw-card-header-c">
                        <img
                            src={logoC}
                            alt="HearBe"
                            className="pw-logo-c"
                            style={{ cursor: 'pointer' }}
                            onClick={() => navigate('/main')}
                        />
                        <h1>비밀번호 재설정</h1>
                        <p className="pw-desc-c">안전한 서비스 이용을 위해 본인 확인이 필요합니다.</p>
                    </div>

                    {step === 1 ? (
                            <div className="pw-step-form-c">
                            <div className="pw-input-group-c">
                                <label>이름</label>
                                <div className="pw-input-wrapper-c">
                                    <Smile className="pw-icon-c" size={32} />
                                    <input
                                        type="text"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        placeholder="성함 입력"
                                    />
                                </div>
                            </div>

                            <div className="pw-input-group-c">
                                <label>아이디</label>
                                <div className="pw-input-wrapper-c">
                                    <User className="pw-icon-c" size={32} />
                                    <input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        placeholder="아이디 입력"
                                    />
                                </div>
                            </div>

                            <div className="pw-input-group-c">
                                <label>이메일</label>
                                <div className="pw-input-flex-c">
                                    <div className="pw-input-wrapper-c flex-1-c">
                                        <Mail className="pw-icon-c" size={32} />
                                        <input
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            placeholder="mail@example.com"
                                        />
                                    </div>
                                    <button onClick={handleSendVerification} className="pw-action-btn-c cursor-pointer">
                                        {isSent ? '재발송' : '인증요청'}
                                    </button>
                                </div>
                            </div>

                            {isSent && (
                                <div className="pw-verify-section-c animate-fade-in-c">
                                    <div className="pw-input-group-c">
                                        <label>인증번호</label>
                                        <div className="pw-input-flex-c">
                                            <input
                                                type="text"
                                                value={verificationCode}
                                                onChange={(e) => setVerificationCode(e.target.value)}
                                                placeholder="6자리 숫자 입력"
                                                className="pw-code-input-c flex-1-c"
                                            />
                                            <button onClick={handleVerifyCode} className="pw-confirm-btn-c cursor-pointer">
                                                확인
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <button
                                onClick={handleNextStep}
                                className={`pw-submit-btn-c active cursor-pointer`}
                            >
                                비밀번호 재설정
                            </button>
                        </div>
                    ) : (
                        <form onSubmit={handleResetPassword} className="pw-step-form-c animate-fade-in-c">
                            <div className="pw-input-group-c">
                                <label>새 비밀번호</label>
                                <div className="pw-input-wrapper-c">
                                    <Lock className="pw-icon-c" size={20} />
                                    <input
                                        type={showNewPassword ? "text" : "password"}
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="새 비밀번호 입력"
                                        required
                                        style={{ paddingRight: '45px' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowNewPassword(!showNewPassword)}
                                        style={{
                                            position: 'absolute',
                                            right: '15px',
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            padding: 0,
                                            display: 'flex',
                                            alignItems: 'center',
                                            color: '#9ca3af'
                                        }}
                                    >
                                        {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                    </button>
                                </div>
                                {newPassword.length > 0 && (
                                    <div style={{ marginTop: '8px', paddingLeft: '5px', textAlign: 'left' }}>
                                        {newPassword.length >= 8 && newPassword.length <= 20 && /[a-zA-Z]/.test(newPassword) && /[0-9]/.test(newPassword) ? (
                                            <p className="pw-condition-text satisfied">✓ 사용 가능한 비밀번호입니다</p>
                                        ) : (
                                            <>
                                                {!(newPassword.length >= 8 && newPassword.length <= 20) && (
                                                    <p className="pw-condition-text unsatisfied">• 8~20자 이내여야 합니다</p>
                                                )}
                                                {!/[a-zA-Z]/.test(newPassword) && (
                                                    <p className="pw-condition-text unsatisfied">• 영문이 포함되어야 합니다</p>
                                                )}
                                                {!/[0-9]/.test(newPassword) && (
                                                    <p className="pw-condition-text unsatisfied">• 숫자가 포함되어야 합니다</p>
                                                )}
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="pw-input-group-c">
                                <label>비밀번호 확인</label>
                                <div className="pw-input-wrapper-c">
                                    <Lock className="pw-icon-c" size={20} />
                                    <input
                                        type={showConfirmPassword ? "text" : "password"}
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        placeholder="다시 한번 입력"
                                        required
                                        style={{ paddingRight: '45px' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        style={{
                                            position: 'absolute',
                                            right: '15px',
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            padding: 0,
                                            display: 'flex',
                                            alignItems: 'center',
                                            color: '#9ca3af'
                                        }}
                                    >
                                        {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                    </button>
                                </div>
                            </div>

                            <button type="submit" className="pw-submit-btn-c active cursor-pointer">
                                비밀번호 재설정
                            </button>
                        </form>
                    )}
                </div>
            </main>


        </div>
    );
};

export default FindPasswordC;
