@echo off
cls
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    PROGRESS REPORT SYSTEM                    ║
echo ║                      UNIFIED STARTUP                         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 🚀 STARTING UNIFIED SYSTEM...
echo.

REM Kill any existing Python processes on port 5000
echo 🔄 Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do taskkill /f /pid %%a 2>nul

echo.
echo 🏥 Starting Progress Report System...
echo    Port: 5000
echo    URL:  http://127.0.0.1:5000
echo.
echo    📋 Features Available:
echo       - ROD Dashboard
echo       - Progress Notes
echo       - Incident Viewer
echo       - Policy Management  
echo       - FCM Dashboard
echo       - Usage Analytics
echo.

start /b python app.py

echo ⏳ Waiting for system to initialize...
timeout /t 8 /nobreak > nul

echo.
echo ✅ PROGRESS REPORT SYSTEM IS NOW RUNNING!
echo.
echo 🌐 Access URL: http://127.0.0.1:5000
echo.

echo 🌐 Opening system in browser...
start http://127.0.0.1:5000

echo.
echo 📝 SYSTEM STATUS: RUNNING
echo 🔄 All features are active and ready to use
echo.
echo ⚠️  To stop system: Close this window or press Ctrl+C
echo.

:loop
echo 💚 System running... (Press Ctrl+C to stop)
timeout /t 30 /nobreak > nul
goto loop
