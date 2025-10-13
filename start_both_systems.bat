@echo off
echo ========================================
echo Progress Report - Dual System Startup
echo ========================================
echo.
echo Starting both systems simultaneously...
echo Core System (ROD + Progress Notes): http://127.0.0.1:5000
echo Admin System (Incident + Policy + FCM): http://127.0.0.1:5001
echo.

echo [1/2] Starting Core System...
start "Progress Report - Core System" cmd /k "echo Starting Core System on Port 5000... && python app.py"

echo [2/2] Starting Admin System...
start "Progress Report - Admin System" cmd /k "echo Starting Admin System on Port 5001... && cd admin_system && python admin_app.py"

echo.
echo ✅ Both systems are starting up!
echo.
echo 🌐 Access URLs:
echo   Core System:  http://127.0.0.1:5000
echo   Admin System: http://127.0.0.1:5001
echo.
echo 📝 Note: Two command windows will open for each system
echo 🔄 Wait a few seconds for systems to fully start
echo.
timeout /t 5 /nobreak > nul
echo Systems should be ready now!
echo.
pause
