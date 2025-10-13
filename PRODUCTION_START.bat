@echo off
cls
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    PROGRESS REPORT SYSTEM                    ║
echo ║                     PRODUCTION STARTUP                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 🚀 STARTING PRODUCTION SYSTEM...
echo.

REM Kill any existing Python processes
echo 🔄 Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do taskkill /f /pid %%a 2>nul

echo.
echo 🏥 Starting Unified Progress Report System...
echo    Port: 5000
echo    URL:  http://127.0.0.1:5000
echo.
echo    📋 Integrated Features:
echo       ✅ ROD Dashboard
echo       ✅ Progress Notes
echo       ✅ Incident Viewer
echo       ✅ Policy Management  
echo       ✅ FCM Dashboard
echo       ✅ Usage Analytics
echo       ✅ Admin Settings
echo.

start /b python app.py

echo ⏳ Initializing system...
timeout /t 10 /nobreak > nul

echo.
echo ✅ PRODUCTION SYSTEM IS RUNNING!
echo.
echo 🌐 Access URL: http://127.0.0.1:5000
echo.
echo 👥 User Access:
echo    - ROD Users: Direct dashboard access
echo    - Clinical Staff: Progress notes
echo    - Administrators: Full system access
echo.

echo 🌐 Opening system in browser...
start http://127.0.0.1:5000

echo.
echo 📝 PRODUCTION STATUS: ACTIVE
echo 🔄 All features unified in single system
echo.
echo ⚠️  To stop system: Close this window or press Ctrl+C
echo.

:loop
echo 💚 Production system running... (Press Ctrl+C to stop)
timeout /t 60 /nobreak > nul
goto loop
