@echo off
title Progress Report - System Launcher
cls

echo.
echo  ██████╗ ██████╗  ██████╗  ██████╗ ██████╗ ███████╗███████╗███████╗
echo  ██╔══██╗██╔══██╗██╔═══██╗██╔════╝ ██╔══██╗██╔════╝██╔════╝██╔════╝
echo  ██████╔╝██████╔╝██║   ██║██║  ███╗██████╔╝█████╗  ███████╗███████╗
echo  ██╔═══╝ ██╔══██╗██║   ██║██║   ██║██╔══██╗██╔══╝  ╚════██║╚════██║
echo  ██║     ██║  ██║╚██████╔╝╚██████╔╝██║  ██║███████╗███████║███████║
echo  ╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
echo.
echo                    REPORT SYSTEM - DUAL STARTUP
echo.

echo 🚀 Starting Core System (Port 5000)...
start /min "Core-System" cmd /c "python app.py"

timeout /t 2 /nobreak > nul

echo 🛡️ Starting Admin System (Port 5001)...
start /min "Admin-System" cmd /c "cd admin_system && python admin_app.py"

echo.
echo ✅ Both systems are now starting!
echo.
echo 🌐 Access URLs:
echo    Core System:  http://127.0.0.1:5000
echo    Admin System: http://127.0.0.1:5001
echo.
echo 📝 Systems are running in background
echo 🔄 Please wait 10 seconds for full startup...

timeout /t 10 /nobreak > nul

echo.
echo 🎉 Systems should be ready now!
echo.
echo Press any key to open both systems in browser...
pause > nul

start http://127.0.0.1:5000
timeout /t 2 /nobreak > nul
start http://127.0.0.1:5001

echo.
echo 🌐 Both systems opened in browser!
echo.
echo To stop systems: Close this window or press Ctrl+C
pause
