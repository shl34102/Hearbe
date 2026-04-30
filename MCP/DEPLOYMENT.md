# MCPDesktop 배포 가이드 (간단 버전)

## 📦 배포 담당자에게 전달할 것

1. **MCP 프로젝트 전체** (이미 Extension 자동 로드 코드 포함)

2. **빌드 스크립트:**
   - `MCP/build_mcp.bat` (PyInstaller 빌드)

3. **배포 준비 방법:**

```batch
# 1단계: MCP 빌드
cd MCP
build_mcp.bat

# 2단계: Extension 복사
cd dist\MCPDesktop
mkdir _internal\hearbe-extension
xcopy ..\..\..\Frontend\hearbe-extension\* _internal\hearbe-extension\ /E /I /Y

# 3단계: Zip 압축
cd ..
Compress-Archive -Path MCPDesktop -DestinationPath MCPDesktop_v1.0.zip
```

4. **또는 자동화 스크립트 작성:**

```batch
@echo off
REM MCP 빌드 및 배포 자동화

echo [1/3] Building MCP...
cd MCP
call build_mcp.bat
if %ERRORLEVEL% NEQ 0 exit /b 1

echo [2/3] Preparing deployment package...
cd dist\MCPDesktop
mkdir _internal\hearbe-extension
xcopy ..\..\..\Frontend\hearbe-extension\* _internal\hearbe-extension\ /E /I /Y

echo [3/3] Creating zip archive...
cd ..
powershell Compress-Archive -Path MCPDesktop -DestinationPath MCPDesktop_v1.0.zip -Force

echo [SUCCESS] Deployment package ready: dist\MCPDesktop_v1.0.zip
```

## ✅ 배포 패키지 검증

```
MCPDesktop/
├── MCPDesktop.exe
└── _internal/
    ├── hearbe-extension/  ← 이 폴더 필수!
    │   ├── manifest.json
    │   ├── background.js
    │   ├── content.js
    │   └── content.css
    └── ... (기타 파일들)
```

## 🚀 사용자 사용법

1. Zip 다운로드
2. 압축 해제
3. `MCPDesktop.exe` 실행

→ Chrome Extension 자동 로드 ✅

---

## ⚠️ Build Process Notes

### Configuration File Naming

The application uses `config.env` instead of `.env` for configuration.

**Reason:** Windows Defender/SmartScreen may delete dot-prefixed files (`.env`) when running unsigned executables after security warnings.

**Files involved:**
- [config.env](MCP/config.env) - Configuration file (renamed from `.env`)
- [core/config.py](MCP/core/config.py) - Loads `config.env` with priority over `.env`
- [build_mcp.bat](MCP/build_mcp.bat) - Bundles `config.env` into the build

### ZIP Archive Structure

The build script uses Windows `tar` command to create the ZIP:

```batch
pushd "dist\MCPDesktop"
tar -a -c -f "..\MCPDesktop.zip" MCPDesktop.exe _internal
popd
```

**Why this approach:**
- Avoids wrapper folder issue (zip should extract directly to `MCPDesktop.exe` + `_internal/`)
- Avoids `./` prefix in paths that some archivers add
- Uses built-in Windows 10+ `tar` instead of PowerShell (avoids execution policy issues)

### Known Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Opens Google instead of target URL | `config.env` missing or Windows Defender deleted it | Ensure `config.env` exists with `HOME_URL` |
| Extra wrapper folder after extraction | `tar` zipped the folder instead of contents | Use explicit file names in `tar` command |
| `.env` disappears after security warning | Windows Defender blocks dot-prefixed files on unsigned exe | Use `config.env` naming |

### Build Checklist

- [ ] `config.env` contains correct `HOME_URL`
- [ ] Virtual environment exists (`venv/`)
- [ ] Chrome extension exists at `../Frontend/hearbe-extension/`
- [ ] After build, verify ZIP structure with: `tar -tf dist\MCPDesktop.zip`
