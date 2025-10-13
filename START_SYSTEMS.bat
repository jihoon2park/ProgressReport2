@echo off
title Progress Report System

echo Starting Progress Report System...
echo.

echo System URL: http://127.0.0.1:5000
echo - ROD Dashboard
echo - Progress Notes  
echo - Incident Viewer
echo - Policy Management
echo - FCM Dashboard
echo.

start /b python app.py

echo.
echo System starting...
timeout /t 5 > nul

echo Opening in browser...
start http://127.0.0.1:5000

echo.
echo System is running! Press any key to stop...
pause > nul

echo Stopping system...
taskkill /f /im python.exe 2>nul
echo Done.
