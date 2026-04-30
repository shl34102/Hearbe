import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import Swal from 'sweetalert2';
import { Eye, EyeOff } from 'lucide-react';
import logoC from '../../assets/logoC.png';
import { authAPI } from '../../services/authAPI';
import { resolveMallRouteFromAuthResponse } from '../../utils/userTypeRoute';
import { useAutoLogin } from '../../hooks/useAutoLogin';
import './LoginC.css';

const LoginC = () => {
    const navigate = useNavigate();
    const [showPassword, setShowPassword] = useState(false);
    const [id, setId] = useState('');
    const [password, setPassword] = useState('');
    const [rememberLogin, setRememberLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);



    useAutoLogin({ fallbackRoute: '/C/mall', savedIdKey: 'savedLoginId_c', setId, setRememberLogin, setIsLoading });

    const handleLogin = async (e, loginId = id, loginPassword = password, isAuto = false) => {
        if (e) e.preventDefault();

        if (!loginId || !loginPassword) {
            Swal.fire({
                icon: 'warning',
                text: '아이디와 비밀번호를 입력해주세요.',
                confirmButtonColor: '#7c3aed',
                confirmButtonText: '확인'
            });
            return;
        }

        setIsLoading(true);
        try {
            const response = await authAPI.login(loginId, loginPassword);

            if (rememberLogin) {
                localStorage.setItem('savedLoginId_c', loginId);
            } else {
                localStorage.removeItem('savedLoginId_c');
                // 로그인 유지 미체크 시 리프레시 토큰 삭제 (다음 방문 시 자동로그인 방지)
                localStorage.removeItem('refreshToken');
            }

            localStorage.removeItem('savedLoginPassword_C');

            if (response.data && response.data.id) {
                localStorage.setItem('user_id', response.data.id);
                localStorage.setItem('username', loginId);
            }
            if (response.data && response.data.name) {
                localStorage.setItem('user_name', response.data.name);
            }

            navigate(resolveMallRouteFromAuthResponse(response, '/C/mall'));
        } catch (error) {
            console.error("Login failed:", error);
            if (!isAuto) {
                let errorMessage = error.message || "로그인에 실패했습니다.";

                if (error.status === 404 || errorMessage.includes('존재하지') || errorMessage.includes('아이디')) {
                    errorMessage = "회원이 아닙니다. \n회원가입을 진행해주세요.";
                } else if (error.status === 401 || errorMessage.includes('비밀번호')) {
                    errorMessage = "아이디 또는 비밀번호가 틀립니다.";
                }

                Swal.fire({
                    icon: 'error',
                    title: '로그인 실패',
                    text: errorMessage,
                    confirmButtonColor: '#7c3aed',
                    confirmButtonText: '확인'
                });
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="login-c-page">
            <main className="login-c-content">
                <div className="login-c-card">
                    <div className="logo-area-c">
                        <img
                            src={logoC}
                            alt="HearBe Logo"
                            className="logo-image-c"
                            onClick={() => navigate('/main')}
                            style={{ cursor: 'pointer' }}
                        />
                    </div>

                    <form className="login-c-form" onSubmit={(e) => handleLogin(e)}>
                        <input
                            type="text"
                            placeholder="아이디 입력"
                            className="login-input-c"
                            value={id}
                            onChange={(e) => setId(e.target.value)}
                        />

                        <div className="password-wrapper-c">
                            <input
                                type={showPassword ? "text" : "password"}
                                placeholder="비밀번호 입력"
                                className="login-input-c"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                            <button type="button" onClick={() => setShowPassword(!showPassword)}>
                                {showPassword ? <EyeOff size={32} /> : <Eye size={32} />}
                            </button>
                        </div>

                        <button type="submit" className="login-submit-btn-c" disabled={isLoading}>
                            {isLoading ? '로그인 중...' : '로그인'}
                        </button>

                        <div className="login-keep-c">
                            <input
                                type="checkbox"
                                id="rememberLogin"
                                checked={rememberLogin}
                                onChange={(e) => setRememberLogin(e.target.checked)}
                            />
                            <label htmlFor="rememberLogin">로그인 유지</label>
                        </div>

                        <div className="login-links-c">
                            <Link to="/C/findId">아이디 찾기</Link> | <Link to="/C/findPassword">비밀번호 재설정</Link> | <Link to="/C/signup">회원가입</Link>
                        </div>
                    </form>
                </div>
            </main>


        </div>
    );
};

export default LoginC;
