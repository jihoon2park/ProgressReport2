@echo off
echo ========================================
echo Flask Server Restart
echo ========================================
echo.

REM Stop processes using port 5000
echo [1/3] Stopping existing server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo   Stopping process PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM Wait
echo [2/3] Waiting 2 seconds...
timeout /t 2 /nobreak >nul

REM Start server
echo [3/3] Starting server...
echo.
echo ========================================
echo Server starting...
echo ========================================
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Start server
python app.py

