@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_mcp_test.ps1" %*
endlocal

