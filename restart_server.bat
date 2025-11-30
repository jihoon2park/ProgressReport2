@echo off
echo ========================================
echo Flask Server Restart Script
echo ========================================
echo.

REM 포트 5000 사용 중인 프로세스 확인 및 종료
echo [1/4] Checking for existing server on port 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo Found process on port 5000: PID %%a
    echo Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

REM Python 프로세스 중 app.py 관련 확인
echo [2/4] Checking for running app.py processes...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID:"') do (
    set PID=%%a
    set PID=!PID: =!
    for /f "delims=" %%b in ('wmic process where "ProcessId=!PID!" get CommandLine /format:list ^| findstr "CommandLine"') do (
        set CMD=%%b
        echo !CMD! | findstr /i "app.py" >nul
        if !errorlevel! equ 0 (
            echo Killing app.py process: !PID!
            taskkill /F /PID !PID! >nul 2>&1
        )
    )
)

REM 잠시 대기
echo [3/4] Waiting for processes to terminate...
timeout /t 2 /nobreak >nul

REM 가상 환경 활성화
echo [4/4] Starting server...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 서버 시작
echo.
echo ========================================
echo Starting Flask Server...
echo ========================================
echo.

python app.py

pause

