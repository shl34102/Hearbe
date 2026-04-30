@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_mcp_scripted_input.ps1" %*
endlocal

