@echo off
chcp 65001 > nul
echo 🔍 IIS 서버 로그 모니터링 도구
echo =====================================
echo.

:menu
echo 선택하세요:
echo 1. 로그 파일 목록 보기
echo 2. app.log 실시간 모니터링
echo 3. error.log 실시간 모니터링
echo 4. access.log 실시간 모니터링
echo 5. 모든 로그 파일 보기 (마지막 50줄)
echo 6. wfastcgi.log 보기
echo 7. 종료
echo.
set /p choice="선택 (1-7): "

if "%choice%"=="1" (
    python view_logs.py --list
    pause
    goto menu
)

if "%choice%"=="2" (
    echo app.log 실시간 모니터링 시작... (Ctrl+C로 중단)
    python view_logs.py --file app.log --follow
    pause
    goto menu
)

if "%choice%"=="3" (
    echo error.log 실시간 모니터링 시작... (Ctrl+C로 중단)
    python view_logs.py --file error.log --follow
    pause
    goto menu
)

if "%choice%"=="4" (
    echo access.log 실시간 모니터링 시작... (Ctrl+C로 중단)
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
    echo wfastcgi.log 보기 (마지막 100줄)
    if exist wfastcgi.log (
        python view_logs.py --file wfastcgi.log --lines 100
    ) else (
        echo wfastcgi.log 파일이 없습니다.
    )
    pause
    goto menu
)

if "%choice%"=="7" (
    echo 종료합니다.
    exit
)

echo 잘못된 선택입니다.
pause
goto menu
