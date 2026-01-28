@echo off
chcp 65001 > nul
echo 🔍 IIS Server Log Monitoring Tool
echo =====================================
echo.

:menu
echo Please select:
echo 1. View log file list
echo 2. Real-time monitoring of app.log
echo 3. Real-time monitoring of error.log
echo 4. Real-time monitoring of access.log
echo 5. View all log files (last 50 lines)
echo 6. View wfastcgi.log
echo 7. Exit
echo.
set /p choice="Select (1-7): "

if "%choice%"=="1" (
    python view_logs.py --list
    pause
    goto menu
)

if "%choice%"=="2" (
    echo Starting real-time monitoring of app.log... (Press Ctrl+C to stop)
    python view_logs.py --file app.log --follow
    pause
    goto menu
)

if "%choice%"=="3" (
    echo Starting real-time monitoring of error.log... (Press Ctrl+C to stop)
    python view_logs.py --file error.log --follow
    pause
    goto menu
)

if "%choice%"=="4" (
    echo Starting real-time monitoring of access.log... (Press Ctrl+C to stop)
    python view_logs.py --file access.log --follow
    pause
    goto menu
)

if "%choice%"=="5" (
    python view_logs.py --all
    pause
    goto menu
)

if "%choice%"=="6" (
    echo Viewing wfastcgi.log (last 100 lines)
    if exist wfastcgi.log (
        python view_logs.py --file wfastcgi.log --lines 100
    ) else (
        echo wfastcgi.log file does not exist.
    )
    pause
    goto menu
)

if "%choice%"=="7" (
    echo Exiting.
    exit
)

echo Invalid selection.
pause
goto menu
