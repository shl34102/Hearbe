// 폼 검증 함수

// 아이디 검증
export const validateUsername = (username) => {
    if (!username || username.trim() === '') {
        return '아이디를 입력해주세요.';
    }

    if (username.length < 4) {
        return '아이디는 4자 이상이어야 합니다.';
    }

    if (username.length > 20) {
        return '아이디는 20자 이하여야 합니다.';
    }

    if (!/^[a-zA-Z0-9]+$/.test(username)) {
        return '아이디는 영문, 숫자만 사용 가능합니다.';
    }

    // 영문과 숫자 모두 포함 필수
    const hasLetter = /[a-zA-Z]/.test(username);
    const hasNumber = /[0-9]/.test(username);

    if (!hasLetter || !hasNumber) {
        return '아이디는 영문과 숫자를 모두 포함해야 합니다.';
    }

    return null; // 에러 없음
};

// 비밀번호 검증
export const validatePassword = (password) => {
    if (!password || password.trim() === '') {
        return '비밀번호를 입력해주세요.';
    }

    if (password.length < 8) {
        return '비밀번호는 8자 이상이어야 합니다.';
    }

    if (password.length > 20) {
        return '비밀번호는 20자 이하여야 합니다.';
    }

    // 영문과 숫자 모두 포함 필수
    const hasLetter = /[a-zA-Z]/.test(password);
    const hasNumber = /[0-9]/.test(password);

    if (!hasLetter || !hasNumber) {
        return '비밀번호는 영문과 숫자를 모두 포함해야 합니다.';
    }

    return null;
};

// 비밀번호 확인 검증
export const validatePasswordConfirm = (password, passwordConfirm) => {
    if (!passwordConfirm || passwordConfirm.trim() === '') {
        return '비밀번호 확인을 입력해주세요.';
    }

    if (password !== passwordConfirm) {
        return '비밀번호가 일치하지 않습니다.';
    }

    return null;
};

// 이메일 검증
export const validateEmail = (email) => {
    if (!email || email.trim() === '') {
        return '이메일을 입력해주세요.';
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return '올바른 이메일 형식이 아닙니다.';
    }

    return null;
};

// 이름 검증
export const validateName = (name) => {
    if (!name || name.trim() === '') {
        return '이름을 입력해주세요.';
    }

    if (name.length < 2) {
        return '이름은 2자 이상이어야 합니다.';
    }

    if (name.length > 15) {
        return '이름은 15자 이하여야 합니다.';
    }

    if (!/^[가-힣a-zA-Z\s]+$/.test(name)) {
        return '이름은 한글 또는 영문만 사용 가능합니다.';
    }

    return null;
};
