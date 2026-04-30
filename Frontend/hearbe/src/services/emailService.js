import emailjs from '@emailjs/browser';

// EmailJS 설정
const EMAILJS_SERVICE_ID = import.meta.env.VITE_EMAILJS_SERVICE_ID || 'YOUR_SERVICE_ID';
const EMAILJS_TEMPLATE_ID = import.meta.env.VITE_EMAILJS_TEMPLATE_ID || 'YOUR_TEMPLATE_ID';
const EMAILJS_PUBLIC_KEY = import.meta.env.VITE_EMAILJS_PUBLIC_KEY || 'YOUR_PUBLIC_KEY';


// 인증번호 저장소
const verificationStore = new Map();

// 6자리 인증번호 생성
const generateCode = () => {
    return Math.floor(100000 + Math.random() * 900000).toString();
};

export const emailService = {
    // 인증번호 발송
    sendVerificationCode: async (email, userName = '회원') => {
        const code = generateCode();
        const expiresAt = Date.now() + 180000; // 3분 후 만료

        // 인증번호 저장
        verificationStore.set(email, { code, expiresAt });

        // 이메일 발송
        try {
            await emailjs.send(
                EMAILJS_SERVICE_ID,
                EMAILJS_TEMPLATE_ID,
                {
                    email: email,
                    to_name: userName,
                    verification_code: code,
                    expire_minutes: '3',
                },
                EMAILJS_PUBLIC_KEY
            );
            return { success: true, message: '인증번호가 전송되었습니다.' };
        } catch (error) {
            console.error('EmailJS Error:', error);
            throw new Error('이메일 전송에 실패했습니다. 잠시 후 다시 시도해주세요.');
        }
    },

    // 인증번호 확인
    verifyCode: (email, inputCode) => {
        const stored = verificationStore.get(email);

        if (!stored) {
            throw new Error('인증번호를 먼저 요청해주세요.');
        }

        if (Date.now() > stored.expiresAt) {
            verificationStore.delete(email);
            throw new Error('인증번호가 만료되었습니다. 다시 요청해주세요.');
        }

        if (stored.code !== inputCode) {
            throw new Error('인증번호가 일치하지 않습니다.');
        }

        // 인증 성공 시 삭제
        verificationStore.delete(email);
        return { success: true, message: '인증이 완료되었습니다.' };
    },

    // 남은 시간 확인
    getRemainingTime: (email) => {
        const stored = verificationStore.get(email);
        if (!stored) return 0;

        const remaining = Math.max(0, Math.floor((stored.expiresAt - Date.now()) / 1000));
        return remaining;
    }
};
