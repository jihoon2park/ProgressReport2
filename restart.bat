@echo off
echo ============================================
echo Progress Report - App Restart
echo ============================================
echo.

echo [1/3] Stopping Python processes...
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak > nul
echo Done!
echo.

echo [2/3] Verifying processes stopped...
tasklist | findstr python.exe
if %errorlevel% equ 0 (
    echo Warning: Python still running, trying again...
    taskkill /F /IM python.exe 2>nul
    timeout /t 2 /nobreak > nul
)
echo Done!
echo.

echo [3/3] Starting app with updated code...
start "Progress Report" python app.py
timeout /t 3 /nobreak > nul
echo.

echo ============================================
echo App restarted successfully!
echo ============================================
echo.
echo URL: http://127.0.0.1:5000
echo.
echo Please wait 5-10 seconds for app to fully start
echo Then check logs for errors
echo.
pause


