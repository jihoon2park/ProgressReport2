@echo off
echo Progress Report IIS 배포 스크립트
echo ===============================

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 이 스크립트는 관리자 권한으로 실행해야 합니다.
    pause
    exit /b 1
)

REM 필요한 디렉토리 생성
echo 디렉토리 생성 중...
if not exist "C:\inetpub\wwwroot\ProgressReport" mkdir "C:\inetpub\wwwroot\ProgressReport"
if not exist "C:\inetpub\wwwroot\ProgressReport\logs" mkdir "C:\inetpub\wwwroot\ProgressReport\logs"
if not exist "C:\inetpub\wwwroot\ProgressReport\data" mkdir "C:\inetpub\wwwroot\ProgressReport\data"

REM 파일 복사
echo 파일 복사 중...
xcopy /Y /E /I "*.py" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "templates" "C:\inetpub\wwwroot\ProgressReport\templates\"
xcopy /Y /E /I "static" "C:\inetpub\wwwroot\ProgressReport\static\"
xcopy /Y /E /I "web.config" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "requirements.txt" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "database_schema.sql" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "production_setup.py" "C:\inetpub\wwwroot\ProgressReport\"

REM Python 패키지 설치
echo Python 패키지 설치 중...
pip install -r requirements.txt
pip install wfastcgi

REM 프로덕션 환경 설정 (DB 초기화, API 키 마이그레이션 등)
echo 프로덕션 환경 설정 중...
cd "C:\inetpub\wwwroot\ProgressReport"
python production_setup.py

REM wfastcgi 활성화
echo wfastcgi 활성화 중...
wfastcgi-enable

REM IIS 애플리케이션 풀 설정
echo IIS 애플리케이션 풀 설정 중...
%windir%\system32\inetsrv\appcmd.exe set apppool /apppool.name:ProgressReport /managedRuntimeVersion:""
%windir%\system32\inetsrv\appcmd.exe set apppool /apppool.name:ProgressReport /processModel.identityType:ApplicationPoolIdentity

REM IIS 사이트 설정
echo IIS 사이트 설정 중...
%windir%\system32\inetsrv\appcmd.exe add site /name:ProgressReport /physicalPath:"C:\inetpub\wwwroot\ProgressReport" /bindings:http/*:80:progressreport.local

REM URL Rewrite 모듈 설치 확인
echo URL Rewrite 모듈 확인 중...
if not exist "%windir%\System32\inetsrv\rewrite.dll" (
    echo URL Rewrite 모듈이 설치되어 있지 않습니다.
    echo https://www.iis.net/downloads/microsoft/url-rewrite 에서 다운로드하여 설치해주세요.
    pause
    exit /b 1
)

echo 배포가 완료되었습니다.
echo 다음 단계:
echo 1. hosts 파일에 progressreport.local을 추가해주세요
echo 2. IIS 관리자에서 ProgressReport 사이트의 인증 설정을 확인해주세요
echo 3. 필요한 경우 SSL 인증서를 설치해주세요
pause 