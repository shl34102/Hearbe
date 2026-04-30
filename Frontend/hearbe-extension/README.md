## 📁 파일 구조

```
Frontend/hearbe-extension/
├── background.js          # 현재 활성 파일 (서버에 배포되는 버전)
├── background.dev.js      # 개발용 백업
├── manifest.json
├── content.js
└── content.css
```

## 🔄 환경 전환 방법

### 배포 환경 (현재 상태) ✅
`background.js`가 프로덕션 URL을 사용합니다:
```javascript
const HEARBE_APP_URL = "https://i14d108.p.ssafy.io/A/store";
```

### 로컬 개발 환경으로 전환
로컬에서 테스트할 때는 `background.js`의 URL을 수동으로 변경:

**파일: `Frontend/hearbe-extension/background.js`**
```javascript
const HEARBE_APP_URL = "http://localhost:5173/A/store";
```

또는 `background.dev.js` 내용을 복사하여 `background.js`에 덮어쓰기.

## ⚠️ 주의사항

1. **배포 전 확인 필수**: 배포 전에는 반드시 프로덕션 URL로 되돌려야 합니다.
2. **Git 커밋 주의**: `.gitignore`에 개발용 설정이 포함되지 않도록 주의.
3. **Extension 재로드**: URL 변경 후 `chrome://extensions`에서 Extension을 재로드해야 적용됩니다.

## 🚀 개선 방안 (향후)

환경 자동 감지를 위한 빌드 스크립트 추가 예정.
