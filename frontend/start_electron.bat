@echo off
chcp 65001 >nul
title BH3 AI Assistant - Electron
echo ============================================
echo   BH3 AI Assistant - Electron
echo ============================================
echo.
set NODE_ENV=development
set VITE_DEV_SERVER_URL=http://localhost:5173
echo [1] Environment: NODE_ENV=%NODE_ENV%
echo [2] Vite URL: %VITE_DEV_SERVER_URL%
echo [3] Work dir: %CD%
echo [4] Starting Electron...
echo.
d:\TokusCode\bbb_assistant\node_modules\.bin\electron.cmd .
echo.
echo ============================================
echo   Electron exited (code: %ERRORLEVEL%)
echo ============================================
pause
