import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';
import { Eye, EyeOff, User, Lock, Check } from 'lucide-react';
import logo from '../../assets/logoA.png';
import { authAPI } from '../../services/authAPI';
import { resolveMallRouteFromAuthResponse } from '../../utils/userTypeRoute';
import { useAutoLogin } from '../../hooks/useAutoLogin';
import './LoginB.css';

const LoginB = () => {
    const navigate = useNavigate();
    const [id, setId] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [rememberLogin, setRememberLogin] = useState(true);

    useAutoLogin({ fallbackRoute: '/B/mall', savedIdKey: 'savedLoginId_b', setId, setRememberLogin, setIsLoading });

    const handleLogin = async (e, loginId = id, loginPassword = password, isAuto = false) => {
        if (e) e.preventDefault();

        if (!loginId || !loginPassword) {
            if (!isAuto) {
                Swal.fire({
                    icon: 'warning',
                    text: '아이디와 비밀번호를 입력해주세요.',
                    background: '#141C29',
                    color: '#FFF064',
                    confirmButtonColor: '#FFF064',
                    confirmButtonText: '<span style="color:#141C29">확인</span>'
                });
            }
            return;
        }

        setIsLoading(true);
        try {
            const response = await authAPI.login(loginId, loginPassword);

            if (rememberLogin) {
                localStorage.setItem('savedLoginId_b', loginId);
            } else {
                // 로그인 유지를 체크하지 않으면 아이디와 리프레시 토큰 모두 삭제 (철저한 보안)
                localStorage.removeItem('savedLoginId_b');
                localStorage.removeItem('refreshToken');
            }

            localStorage.removeItem('savedLoginPassword');

            navigate(resolveMallRouteFromAuthResponse(response, '/B/mall'));
        } catch (error) {
            console.error('Login Error:', error);
            if (!isAuto) {
                const errorMessage = error?.message || '아이디 또는 비밀번호가 일치하지 않습니다.';
                Swal.fire({
                    icon: 'error',
                    text: errorMessage.includes('존재') || errorMessage.includes('없') ? '회원가입이 필요합니다.' : errorMessage,
                    background: '#141C29',
                    color: '#FFF064',
                    confirmButtonColor: '#FFF064',
                    confirmButtonText: '<span style="color:#141C29">확인</span>'
                });
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="login-a-page-new">
            <main className="login-a-content-new">
                <div className="login-a-card-new">
                    <div className="logo-area-a-new">
                        <img
                            src={logo}
                            alt="Logo"
                            onClick={() => navigate('/main')}
                            className="logo-image-a-new cursor-pointer"
                        />
                    </div>

                    <form className="login-a-form-new" onSubmit={(e) => handleLogin(e)}>
                        <div className="input-with-icon-a-new">
                            <User className="input-icon-a-new" size={32} />
                            <input
                                type="text"
                                placeholder="아이디"
                                className="login-input-a-new"
                                value={id}
                                onChange={(e) => setId(e.target.value)}
                            />
                        </div>

                        <div className="password-wrapper-a-new">
                            <Lock className="input-icon-a-new" size={32} />
                            <input
                                type={showPassword ? "text" : "password"}
                                placeholder="비밀번호"
                                className="login-input-a-new"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                maxLength={6}
                            />
                            <button
                                type="button"
                                className="pw-toggle-a-new"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? <EyeOff size={36} /> : <Eye size={36} />}
                            </button>
                        </div>

                        <div className="login-options-a-new">
                            <label className="checkbox-container-a-new">
                                <input
                                    type="checkbox"
                                    checked={rememberLogin}
                                    onChange={(e) => setRememberLogin(e.target.checked)}
                                />
                                <span className="checkmark-a-new">
                                    {rememberLogin && <Check size={28} strokeWidth={4} className="checked-icon" />}
                                </span>
                                <span className="label-text-a-new">로그인 유지</span>
                            </label>
                        </div>

                        <button
                            type="submit"
                            className="login-submit-btn-a-new"
                            disabled={isLoading}
                        >
                            {isLoading ? '로그인 중...' : '로그인'}
                        </button>

                        <div className="login-footer-links-a-new">
                            <span onClick={() => navigate('/B/findId')} className="cursor-pointer">아이디 찾기</span>
                            <span className="separator-a-new">|</span>
                            <span onClick={() => navigate('/B/findPassword')} className="cursor-pointer">비밀번호 재설정</span>
                            <span className="separator-a-new">|</span>
                            <span onClick={() => navigate('/B/signup')} className="cursor-pointer">회원가입</span>
                        </div>
                    </form>
                </div>
            </main>
        </div>
    );
};

export default LoginB;
