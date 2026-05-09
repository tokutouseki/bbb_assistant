@echo off
chcp 65001 >nul
title BH3 AI Assistant Launcher

echo ==============================================
echo BH3 AI Assistant - Admin Launcher
echo ==============================================
echo.

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with admin privileges
    echo.
) else (
    echo [WARN] Not running as administrator
    echo Attempting to elevate...
    echo.
    echo Click "Yes" in the UAC prompt
    echo.
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo Starting backend service...
start "Backend Service" /D "d:\TokusCode\bbb_assistant\backend" cmd /k "python src/main.py & pause"

echo Waiting for backend to start...
set "attempts=0"
set "max_attempts=30"

:WAIT_LOOP
timeout /t 1 /nobreak >nul 2>&1
powershell -Command "try { Invoke-WebRequest -Uri http://localhost:8000/api/health -Method GET -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }"
if %errorLevel% == 0 (
    echo [OK] Backend service is ready!
    goto OPEN_BROWSER
)

set /a "attempts+=1"
if %attempts% lss %max_attempts% (
    echo [WAIT] Waiting for backend... (%attempts%/%max_attempts%)
    goto WAIT_LOOP
)

echo [WARN] Timeout waiting for backend. Opening browser anyway...

:OPEN_BROWSER
echo Opening frontend...
start "Frontend" http://localhost:8000

echo.
echo ==============================================
echo [DONE] Launch completed!
echo ==============================================
echo.
echo Backend: http://localhost:8000
echo Frontend: Opened in browser
echo.
echo Press any key to close this launcher...
pause >nul