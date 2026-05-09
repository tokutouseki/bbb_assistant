@echo off
chcp 65001 >nul
title BH3 AI Assistant Launcher

echo ==============================================
echo   BH3 AI Assistant - Desktop Launcher
echo ==============================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] Running with admin privileges
    echo.
) else (
    echo [WARN] Not running as administrator
    echo Attempting to elevate...
    echo.
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo [STEP] Cleaning up old processes...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host '[OK] Killed old backend process PID=' $_.OwningProcess }"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host '[OK] Killed old Vite process PID=' $_.OwningProcess }"
echo.

echo [STEP 1/3] Starting backend service...
start "Backend Service" /D "d:\TokusCode\bbb_assistant\backend" cmd /k "python src/main.py"

echo [STEP 2/3] Starting Vite dev server...
start "Vite Dev Server" /D "d:\TokusCode\bbb_assistant\frontend" cmd /k "npx vite --host 0.0.0.0 --port 5173 --strictPort"

echo.
echo ==============================================
echo   Waiting for services to start...
echo   (max 30 seconds each)
echo ==============================================
echo.

echo [CHECK] Backend...
set "attempts=0"

:WAIT_BACKEND
timeout /t 2 /nobreak >nul
set /a "attempts+=1"
powershell -NoProfile -Command "try{$r=Invoke-WebRequest 'http://localhost:8000/api/health/' -UseBasicParsing -TimeoutSec 3; exit 0}catch{exit 1}"
if %ERRORLEVEL% equ 0 (
    echo [OK] Backend is ready! (%attempts% attempts)
    goto CHECK_VITE
)
if %attempts% lss 15 (
    echo [..] Waiting backend... %attempts%/15
    goto WAIT_BACKEND
)
echo [WARN] Backend not responding, continuing anyway...

:CHECK_VITE
echo.
echo [CHECK] Vite...
set "v_attempts=0"

:WAIT_VITE
timeout /t 2 /nobreak >nul
set /a "v_attempts+=1"
powershell -NoProfile -Command "try{$r=Invoke-WebRequest 'http://localhost:5173/' -UseBasicParsing -TimeoutSec 3; exit 0}catch{exit 1}"
if %ERRORLEVEL% equ 0 (
    echo [OK] Vite is ready! (%v_attempts% attempts)
    goto LAUNCH_ELECTRON
)
if %v_attempts% lss 15 (
    echo [..] Waiting Vite... %v_attempts%/15
    goto WAIT_VITE
)
echo [WARN] Vite not responding, continuing anyway...

:LAUNCH_ELECTRON
echo.
echo ==============================================
echo   [STEP 3/3] Launching Electron...
echo ==============================================
echo.
echo   If Electron fails, the cmd window will show errors.
echo   Keep it open to see what went wrong.
echo.

start "BH3 AI Assistant" /D "d:\TokusCode\bbb_assistant\frontend" cmd /k "start_electron.bat"

echo.
echo ==============================================
echo   [DONE] All services launched!
echo ==============================================
echo.
echo   Backend   : http://localhost:8000  ^(api/health/^)
echo   Vite      : http://localhost:5173
echo   Electron  : Desktop window ^(BH3 AI Assistant^)
echo.
echo   Electron errors: Check "BH3 AI Assistant" cmd window
echo.
pause
