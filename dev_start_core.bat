@echo off
title Progress Report - Core Module Development

echo ========================================
echo Core Module Development Environment  
echo ========================================
echo.
echo This is for DEVELOPMENT ONLY
echo Production uses unified system on port 5000
echo.

echo Starting Core Development Module...
echo Port: 5000
echo URL:  http://127.0.0.1:5000
echo.
echo Features:
echo - ROD Dashboard
echo - Progress Notes
echo - Usage Analytics
echo.

python app.py

echo.
echo Core development module stopped.
pause
