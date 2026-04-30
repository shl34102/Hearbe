@echo off
setlocal EnableExtensions
chcp 65001 >nul

REM ===========================================================================
REM 음성지원프로그램 Build Script for Windows
REM - Usage: build_mcp.bat [version]
REM - Example: build_mcp.bat 1.2.0
REM ===========================================================================

set "APP_BASE_NAME=음성지원프로그램"
set "APP_VERSION="

REM Argument parsing
IF /I "%~1"=="-v" (
    set "APP_VERSION=%~2"
) ELSE IF /I "%~1"=="--version" (
    set "APP_VERSION=%~2"
) ELSE (
    set "APP_VERSION=%~1"
)

IF "%APP_VERSION%"=="" (
    set /p APP_VERSION=[INPUT] 버전명을 입력하세요 ^(예: 1.2.0^): 
)

IF "%APP_VERSION%"=="" (
    echo [ERROR] 버전명이 비어 있습니다. 빌드를 종료합니다.
    pause
    exit /b 1
)

set "BUILD_NAME=%APP_BASE_NAME%_%APP_VERSION%"
set "LATEST_ZIP_NAME=%APP_BASE_NAME%_latest.zip"

echo [INFO] Build target: %BUILD_NAME%

REM Check for virtual environment activation script
IF EXIST "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    CALL venv\Scripts\activate.bat
) ELSE (
    echo [ERROR] Virtual environment not found. Please ensure 'venv' directory exists.
    pause
    exit /b 1
)

echo [INFO] Starting PyInstaller build process for '%BUILD_NAME%'...

REM ---------------------------------------------------------------------------
REM PyInstaller Configuration:
REM -y: Overwrite existing output directory without confirmation.
REM --clean: Clear PyInstaller cache and remove temporary files before building.
REM --name: Specify the name of the executable and output directory.
REM --onedir: Create a bundled directory containing the executable and dependencies.
REM --noconsole: Disable the terminal window for GUI-based applications.
REM --collect-all: Ensure all submodules and data for 'playwright' are included.
REM --add-data: Bundle files/directories (config.env, Chrome extension) into the build.
REM ---------------------------------------------------------------------------
pyinstaller -y --clean ^
    --name "%BUILD_NAME%" ^
    --onedir ^
    --noconsole ^
    --collect-all playwright ^
    --add-data "config.env;." ^
    --add-data "..\Frontend\hearbe-extension;hearbe-extension" ^
    main.py

REM Verify build success via exit code
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed. Please review the diagnostic logs above.
    pause
    exit /b %ERRORLEVEL%
)

echo [SUCCESS] Build completed. Output is available in 'dist/%BUILD_NAME%' directory.

REM ---------------------------------------------------------------------------
REM Post-build: Create ZIP archive and copy to Frontend public folder
REM ---------------------------------------------------------------------------
echo [INFO] Creating ZIP archive...
IF EXIST "dist\%BUILD_NAME%.zip" del /Q "dist\%BUILD_NAME%.zip"

REM Using tar (built-in Windows 10+) to avoid PowerShell execution policy issues
REM pushd/popd ensures correct relative paths without ./ prefix
pushd "dist\%BUILD_NAME%"
tar -a -c -f "..\%BUILD_NAME%.zip" "%BUILD_NAME%.exe" _internal
popd

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create ZIP archive.
    pause
    exit /b %ERRORLEVEL%
)

echo [INFO] Copying ZIP to Frontend public folder...
IF NOT EXIST "..\Frontend\hearbe\public\downloads" mkdir "..\Frontend\hearbe\public\downloads"
copy /Y "dist\%BUILD_NAME%.zip" "..\Frontend\hearbe\public\downloads\%BUILD_NAME%.zip"
copy /Y "dist\%BUILD_NAME%.zip" "..\Frontend\hearbe\public\downloads\%LATEST_ZIP_NAME%"

echo [INFO] Updating version metadata...
(
    echo { "version": "%APP_VERSION%" }
) > "..\Frontend\hearbe\public\downloads\voice-program-version.json"

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to copy ZIP to Frontend.
    pause
    exit /b %ERRORLEVEL%
)

echo [SUCCESS] %BUILD_NAME%.zip is ready at Frontend/hearbe/public/downloads/
echo [SUCCESS] Latest alias updated: %LATEST_ZIP_NAME%
pause
