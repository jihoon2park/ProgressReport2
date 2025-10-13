@echo off
title Progress Report - Admin Module Development

echo ========================================
echo Admin Module Development Environment
echo ========================================
echo.

REM Ensure we're in the correct directory
cd /d "%~dp0"

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Kill any existing process on port 5001
echo 🔄 Cleaning up existing processes on port 5001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do taskkill /f /pid %%a 2>nul

echo.
echo This is for DEVELOPMENT ONLY
echo Production uses unified system on port 5000
echo.

echo Starting Admin Development Module...
echo Port: 5001 (Development Only)
echo URL:  http://127.0.0.1:5001
echo.

python dev_modules\admin_app.py

echo.
echo Admin development module stopped.
pause
