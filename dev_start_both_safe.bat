@echo off
title Progress Report - Development Environment

echo ========================================
echo Development Environment - Dual Modules
echo ========================================
echo.

REM Ensure we're in the correct directory
cd /d "%~dp0"

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Kill any existing processes
echo 🔄 Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do taskkill /f /pid %%a 2>nul

echo.
echo This is for DEVELOPMENT ONLY
echo Production uses unified system on port 5000
echo.

echo Starting both development modules...
echo.
echo Core Module:  http://127.0.0.1:5000
echo Admin Module: http://127.0.0.1:5001
echo.

echo [1/2] Starting Core Module...
start "Core Development" cmd /k "title Core Module && echo Core Module (Port 5000) && python app.py"

timeout /t 3 /nobreak > nul

echo [2/2] Starting Admin Module...
start "Admin Development" cmd /k "title Admin Module && echo Admin Module (Port 5001) && python dev_modules\admin_app.py"

echo.
echo ✅ Both development modules are starting!
echo.
echo 🌐 Development URLs:
echo   Core:  http://127.0.0.1:5000
echo   Admin: http://127.0.0.1:5001
echo.
echo 📝 Note: This is for development only
echo 🚀 Production uses single unified system
echo.

timeout /t 5 /nobreak > nul
echo Opening development modules in browser...
start http://127.0.0.1:5000
timeout /t 2 /nobreak > nul
start http://127.0.0.1:5001

pause
