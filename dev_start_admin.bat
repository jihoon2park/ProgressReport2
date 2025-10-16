@echo off
title Progress Report - Admin Module Development

echo ========================================
echo Admin Module Development Environment
echo ========================================
echo.
echo This is for DEVELOPMENT ONLY
echo Production uses unified system on port 5000
echo.

echo Starting Admin Development Module...
echo Port: 5001 (Development Only)
echo URL:  http://127.0.0.1:5001
echo.

python dev_modules\admin_app.py

echo.
echo Admin development module stopped.
pause
