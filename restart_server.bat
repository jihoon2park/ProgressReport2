@echo off
echo ========================================
echo Flask Server Restart Script
echo ========================================
echo.

REM Check and terminate processes using port 5000
echo [1/4] Checking for existing server on port 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo Found process on port 5000: PID %%a
    echo Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

REM Check for app.py related processes among Python processes
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

REM Wait briefly
echo [3/4] Waiting for processes to terminate...
timeout /t 2 /nobreak >nul

REM Activate virtual environment
echo [4/4] Starting server...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Start server
echo.
echo ========================================
echo Starting Flask Server...
echo ========================================
echo.

python app.py

pause

