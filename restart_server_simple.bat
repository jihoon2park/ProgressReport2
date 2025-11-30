@echo off
echo ========================================
echo Flask Server Restart
echo ========================================
echo.

REM 포트 5000 사용 중인 프로세스 종료
echo [1/3] Stopping existing server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo   Stopping process PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM 대기
echo [2/3] Waiting 2 seconds...
timeout /t 2 /nobreak >nul

REM 서버 시작
echo [3/3] Starting server...
echo.
echo ========================================
echo Server starting...
echo ========================================
echo.

REM 가상 환경 활성화
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 서버 시작
python app.py

