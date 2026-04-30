﻿import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion as _motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, User, Lock, Eye, EyeOff, Mail, Calendar, Phone, CheckCircle2, PartyPopper } from 'lucide-react';
import { validateUsername, validatePassword, validatePasswordConfirm, validateEmail, validateName } from '../../utils/validation';
import { authAPI } from '../../services/authAPI';
import Swal from 'sweetalert2';
import logoC from '../../assets/logoC.png';
import './SignUpC.css';

const SignUpC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    name: '',
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [agreements, setAgreements] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUsernameChecked, setIsUsernameChecked] = useState(false);
  const [isUsernameAvailable, setIsUsernameAvailable] = useState(false);

  const [termModalState, setTermModalState] = useState({
    isOpen: false,
    title: '',
    content: ''
  });

  const termContents = {
    terms: `제1조 (AI 에이전트 서비스 이용 안내)
본 서비스는 사용자의 편리한 쇼핑을 위해 AI 에이전트 기술을 활용합니다.

AI 브라우저 대리 조작: 사용자가 음성으로 명령하면, HearBe의 AI 에이전트가 가상 브라우저를 통해 실제 쇼핑몰 웹사이트를 사용자를 대신하여 탐색하고 조작합니다. 이는 사용자가 직접 화면을 보고 클릭하는 과정을 AI가 음성 명령에 따라 수행하는 것입니다.

화면 분석 및 정보 제공: AI는 쇼핑몰의 이미지와 텍스트를 실시간으로 분석하여 사용자에게 음성으로 전달합니다. 이 과정에서 정확한 정보 전달을 위해 화면 캡처 및 텍스트 추출이 이루어질 수 있습니다.`,
    privacy: `제2조 (개인정보 수집 및 이용 항목)
서비스 제공을 위해 아래와 같은 정보를 수집합니다. 수집된 정보는 회원 탈퇴 시 또는 법정 보유 기간 종료 시 즉시 파기됩니다.

1. 시각장애인 사용자 (A형, B형)
- 필수 수집 항목: 아이디, 비밀번호, 이름
- 선택 수집 항목: 휴대폰 번호
- 장애인 복지 카드 확인 정보: 카드사, 카드번호 뒤 4자리, 유효기간 (사용자 맞춤형 UI 제공 목적)
- 음성 데이터: 음성 명령 인식 및 처리 (목적 달성 후 즉시 파기)

2. 일반인 및 보호자 사용자 (C형)
- 필수 수집 항목: 아이디, 비밀번호, 이름, 이메일 주소
- 원격 제어 정보: 사용자 브라우저 원격 조종을 위한 접속 로그 및 명령 데이터`,
    security: `제3조 (결제 보안 및 민감 정보 보호)
결제 확인: AI가 사용자를 대신해 결제 단계까지 진입할 수 있으나, 실제 결제 승인은 사용자의 최종 확인(비밀번호 입력 또는 음성 확답)이 있어야만 완료됩니다.

비밀번호 미저장 원칙: 사용자의 결제 비밀번호는 서비스 내 어떠한 장치나 서버에도 저장되지 않으며, 결제 시마다 사용자가 직접 입력하는 것을 원칙으로 합니다.

기기 기반 암호화 등록: 복지 카드 정보 등 서비스 이용을 위해 등록한 민감 정보는 서버에 저장되지 않으며, 사용자가 서비스에 접속한 해당 웹 브라우저 및 기기에만 암호화되어 등록됩니다.

입력 단계 보안: 결제 관련 민감 정보 입력 시에는 AI의 화면 분석 기능을 일시 제한하며, 사용자의 기기 내에서 직접 암호화 처리를 수행하여 정보 유출을 원천 차단합니다.

데이터 비식별화: 음성 및 이미지 분석을 위해 외부 AI 엔진을 이용할 경우, 개인을 식별할 수 없는 데이터 형태로 가공하여 전송합니다.`
  };

  const openTermModal = () => {
    const title = '이용약관 및 개인정보 수집 동의';
    const content = `${termContents.terms}

---------------------------------------------

${termContents.privacy}

---------------------------------------------

${termContents.security}`;

    setTermModalState({ isOpen: true, title, content });
  };

  const closeTermModal = (agree = false) => {
    setTermModalState({ ...termModalState, isOpen: false });
    if (agree) {
      setAgreements(true);
    }
  };

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
    if (errors[field]) {
      setErrors({ ...errors, [field]: null });
    }
    if (field === 'username') {
      setIsUsernameChecked(false);
      setIsUsernameAvailable(false);
    }
  };

  const [matchMessage, setMatchMessage] = useState('');
  const [matchValid, setMatchValid] = useState(false);

  const handlePasswordCheck = () => {
    if (!confirmPassword) {
      setMatchMessage('');
      setMatchValid(false);
      return;
    }

    if (formData.password === confirmPassword) {
      setMatchMessage('비밀번호가 일치합니다.');
      setMatchValid(true);
    } else {
      setMatchMessage('비밀번호가 일치하지 않습니다.');
      setMatchValid(false);
    }
  };

  const handleConfirmPasswordChange = (value) => {
    setConfirmPassword(value);
    if (errors.confirmPassword) {
      setErrors({ ...errors, confirmPassword: null });
    }
    if (matchMessage) {
      setMatchMessage('');
    }
  };

  const handleCheckUsername = async () => {
    // validation.js의 공통 검증 로직 사용
    const idError = validateUsername(formData.username);
    if (idError) {
      Swal.fire({
        icon: 'warning',
        text: idError,
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });
      return;
    }

    try {
      const apiResponse = await authAPI.checkDuplicate(formData.username);
      const isDuplicate = apiResponse.data;

      if (!isDuplicate) {
        setIsUsernameChecked(true);
        setIsUsernameAvailable(true);
        Swal.fire({
          icon: 'success',
          text: '사용 가능한 아이디입니다.',
          confirmButtonColor: '#7c3aed',
          confirmButtonText: '확인'
        });
      } else {
        setIsUsernameChecked(true);
        setIsUsernameAvailable(false);
        Swal.fire({
          icon: 'error',
          text: '이미 사용 중인 아이디입니다.',
          confirmButtonColor: '#7c3aed',
          confirmButtonText: '확인'
        });
      }
    } catch (error) {
      console.error('Username check error:', error);
      Swal.fire({
        icon: 'error',
        text: '아이디 중복 확인에 실패했습니다.',
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });
      setIsUsernameChecked(false); // 에러 발생 시 중복확인 상태 초기화
    }
  };

  const handleEmailBlur = () => {
    if (!formData.email) return;

    if (!formData.email.includes('@')) {
      setErrors((prev) => ({ ...prev, email: '@포함한 유효한 이메일을 입력해주세요' }));
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    if (!emailRegex.test(formData.email)) {
      setErrors((prev) => ({ ...prev, email: '유효한 이메일을 입력해주세요' }));
      return;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const usernameError = validateUsername(formData.username);
    const passwordError = validatePassword(formData.password);
    const confirmPasswordError = validatePasswordConfirm(formData.password, confirmPassword);
    // emailError는 아래에서 별도로 처리하거나 validateEmail 결과 사용
    const nameError = validateName(formData.name);

    if (!formData.email.includes('@')) {
      Swal.fire({
        icon: 'warning',
        text: '@를 포함하여 이메일을 작성해주세요.',
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      Swal.fire({
        icon: 'warning',
        text: '올바른 이메일 주소를 입력해주세요.', // 도메인 포함 여부 등 포괄적 메시지
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });
      return;
    }

    // validateEmail 결과도 확인 (혹시 모를 다른 케이스)
    const emailError = validateEmail(formData.email);


    if (!isUsernameChecked || !isUsernameAvailable) {
      Swal.fire({
        icon: 'warning',
        text: '아이디 중복확인을 해주세요.',
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });
      return;
    }

    if (usernameError || passwordError || confirmPasswordError || emailError || nameError) {
      const errorMsg = [usernameError, passwordError, confirmPasswordError, emailError, nameError].filter(Boolean).join('\n');

      Swal.fire({
        icon: 'warning',
        title: '입력 정보 확인',
        html: errorMsg.replace(/\n/g, '<br/>'), // 줄바꿈 처리를 위해 html 사용
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });

      setErrors({
        username: usernameError,
        password: passwordError,
        confirmPassword: confirmPasswordError,
        email: emailError,
        name: nameError,
      });
      return;
    }

    if (!agreements) {
      Swal.fire({
        icon: 'warning',
        text: '필수 이용약관 및 개인정보 수집에 동의해주세요.',
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });
      return;
    }

    try {
      const payload = {
        username: formData.username,
        password: formData.password,
        password_check: confirmPassword,
        name: formData.name,
        email: formData.email,
        phone_number: null,
        user_type: "GENERAL", // C형 사용자
        simple_password: null,
        welfare_card: null
      };

      const apiResponse = await authAPI.register(payload);
      if (apiResponse.success) {
        setIsModalOpen(true);
      } else {
        Swal.fire({
          icon: 'error',
          text: apiResponse.message || '회원가입에 실패했습니다.',
          confirmButtonColor: '#7c3aed',
          confirmButtonText: '확인'
        });
      }
    } catch (error) {
      console.error('Signup error:', error);
      Swal.fire({
        icon: 'error',
        text: error.message || '회원가입 중 오류가 발생했습니다.',
        confirmButtonColor: '#7c3aed',
        confirmButtonText: '확인'
      });
    }
  };

  const isFormValid =
    isUsernameChecked &&
    isUsernameAvailable &&
    !validatePassword(formData.password) &&
    !validatePasswordConfirm(formData.password, confirmPassword) &&
    !validateName(formData.name) &&
    !validateEmail(formData.email) &&
    agreements;

  return (
    <div className="signup-c-container">
      <main className="signup-c-main">
        <div className="signup-card-c">
          <div className="signup-header-c">
            <img
              src={logoC}
              alt="HearBe Logo"
              className="signup-logo-c"
              style={{ marginBottom: '20px', cursor: 'pointer' }}
              onClick={() => navigate('/main')}
            />
          </div>

          <form onSubmit={handleSubmit} className="signup-form-c">
            <div className="input-section-c">
              <div className={`input-c-group ${errors.username ? 'error' : ''}`}>
                <div className="input-with-button-c">
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => handleChange('username', e.target.value)}
                    placeholder="아이디"
                    className="signup-input-c"
                  />
                  <button
                    type="button"
                    onClick={handleCheckUsername}
                    className={`check-duplicate-btn-c cursor-pointer ${isUsernameChecked && isUsernameAvailable ? 'checked' : ''}`}
                  >
                    {isUsernameChecked && isUsernameAvailable ? '확인완료' : '중복확인'}
                  </button>
                </div>
                {errors.username && <span className="error-text-c">{errors.username}</span>}
                {isUsernameChecked && !isUsernameAvailable && (
                  <span className="error-text-c">이미 사용 중인 아이디입니다.</span>
                )}
              </div>

              <div className={`input-c-group ${errors.password ? 'error' : ''}`}>
                <div className="password-wrapper-c">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => handleChange('password', e.target.value)}
                    placeholder="비밀번호 (8~20자, 영문+숫자)"
                    className={`signup-input-c gray-bg-c ${errors.password ? 'input-error' : ''}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="pw-toggle-c cursor-pointer"
                  >
                    {showPassword ? <EyeOff size={32} color="#94A3B8" /> : <Eye size={32} color="#94A3B8" />}
                  </button>
                </div>

                {formData.password.length > 0 && (
                  <div className="password-conditions-text-group">
                    {formData.password.length >= 8 && formData.password.length <= 20 && /[a-zA-Z]/.test(formData.password) && /[0-9]/.test(formData.password) ? (
                      <p className="pw-condition-text satisfied">✓ 사용 가능한 비밀번호입니다</p>
                    ) : (
                      <>
                        {!(formData.password.length >= 8 && formData.password.length <= 20) && (
                          <p className="pw-condition-text unsatisfied">• 8~20자 이내여야 합니다</p>
                        )}
                        {!/[a-zA-Z]/.test(formData.password) && (
                          <p className="pw-condition-text unsatisfied">• 영문이 포함되어야 합니다</p>
                        )}
                        {!/[0-9]/.test(formData.password) && (
                          <p className="pw-condition-text unsatisfied">• 숫자가 포함되어야 합니다</p>
                        )}
                      </>
                    )}
                  </div>
                )}

                {errors.password && <span className="error-text-c">{errors.password}</span>}
              </div>

              <div className={`input-c-group confirm-pw-group ${errors.confirmPassword ? 'error' : ''}`}>
                <div className="password-wrapper-c">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => handleConfirmPasswordChange(e.target.value)}
                    onMouseLeave={handlePasswordCheck}
                    onBlur={handlePasswordCheck}
                    placeholder="비밀번호 재확인"
                    className="signup-input-c gray-bg-c"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="pw-toggle-c"
                  >
                    {showConfirmPassword ? <EyeOff size={32} color="#94A3B8" /> : <Eye size={32} color="#94A3B8" />}
                  </button>
                </div>
                {matchMessage && (
                  <div style={{ textAlign: 'left', marginTop: '8px', paddingLeft: '5px' }}>
                    <p
                      className={`pw-condition-text ${matchValid ? 'satisfied' : 'unsatisfied'}`}
                      style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      <span style={{ fontSize: matchValid ? '14px' : '8px', lineHeight: '1' }}>
                        {matchValid ? '✓' : '●'}
                      </span>
                      {matchMessage}
                    </p>
                  </div>
                )}
                {errors.confirmPassword && <span className="error-text-c">{errors.confirmPassword}</span>}
              </div >
            </div >

            <hr className="form-divider-c" />

            <div className="input-section-c">
              <div className={`input-c-group ${errors.name ? 'error' : ''}`}>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="이름"
                  className="signup-input-c"
                />
                {errors.name && <span className="error-text-c">{errors.name}</span>}
              </div>
              <div className={`input-c-group ${errors.email ? 'error' : ''}`}>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  onBlur={handleEmailBlur}
                  placeholder="이메일(example@gmail.com)"
                  className="signup-input-c"
                />
                {errors.email && <span className="error-text-c">{errors.email}</span>}
              </div>
            </div>

            <div className="terms-container-c">
              <div className="terms-item-c" style={{ justifyContent: 'space-between' }}>
                <div className="checkbox-row">
                  <input
                    type="checkbox"
                    id="all"
                    checked={agreements}
                    onChange={(e) => setAgreements(e.target.checked)}
                  />
                  <label htmlFor="all" style={{ fontWeight: 'bold' }}>[필수] 이용약관 및 개인정보 수집 동의</label>
                </div>
                <button type="button" className="terms-view-btn-c cursor-pointer" onClick={() => openTermModal('terms')}>보기 &gt;</button>
              </div>
            </div>

            <button
              type="submit"
              className="signup-submit-btn-c cursor-pointer"
            >
              회원 가입
            </button>
          </form >
        </div >
      </main >

      <AnimatePresence>
        {isModalOpen && (
          <div className="modal-overlay-c">
            <_motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="modal-content-c"
            >
              <div className="modal-icon-c">✔</div>
              <h2 className="modal-title-c">가입완료!</h2>
              <p className="modal-desc-c">
                HearBe 회원이 되신 것을 축하드립니다.
              </p>
              <button onClick={() => { setIsModalOpen(false); navigate('/C/login'); }} className="modal-btn-c cursor-pointer">
                확인
              </button>
            </_motion.div>
          </div>
        )}

        {termModalState.isOpen && (
          <div className="modal-overlay-c" onClick={() => closeTermModal(false)}>
            <_motion.div
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 50, opacity: 0 }}
              className="modal-content-c term-modal-c"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="term-modal-header">
                <h3 className="term-title">{termModalState.title}</h3>
                <button onClick={() => closeTermModal(false)} className="close-btn-c cursor-pointer">✕</button>
              </div>
              <div className="term-scroll-box">
                <p className="term-text whitespace-pre-line">{termModalState.content}</p>
              </div>
              <button onClick={() => closeTermModal(true)} className="modal-btn-c term-confirm-btn cursor-pointer">
                확인
              </button>
            </_motion.div>
          </div>
        )}
      </AnimatePresence>


    </div>
  );
};

export default SignUpC;
