@echo off
echo Progress Report IIS Deployment Script
echo ===============================

REM Check administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script must be run with administrator privileges.
    pause
    exit /b 1
)

REM Create necessary directories
echo Creating directories...
if not exist "C:\inetpub\wwwroot\ProgressReport" mkdir "C:\inetpub\wwwroot\ProgressReport"
if not exist "C:\inetpub\wwwroot\ProgressReport\logs" mkdir "C:\inetpub\wwwroot\ProgressReport\logs"
if not exist "C:\inetpub\wwwroot\ProgressReport\data" mkdir "C:\inetpub\wwwroot\ProgressReport\data"

REM Copy files
echo Copying files...
xcopy /Y /E /I "*.py" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "templates" "C:\inetpub\wwwroot\ProgressReport\templates\"
xcopy /Y /E /I "static" "C:\inetpub\wwwroot\ProgressReport\static\"
xcopy /Y /E /I "web.config" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "requirements.txt" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "database_schema.sql" "C:\inetpub\wwwroot\ProgressReport\"
xcopy /Y /E /I "production_setup.py" "C:\inetpub\wwwroot\ProgressReport\"

REM Install Python packages
echo Installing Python packages...
pip install -r requirements.txt
pip install wfastcgi

REM Production environment setup (DB initialization, API key migration, etc.)
echo Setting up production environment...
cd "C:\inetpub\wwwroot\ProgressReport"
python production_setup.py

REM Modify DB schema (sync production and development servers)
echo Modifying DB schema...
python fix_prod_schema.py

REM Enable wfastcgi
echo Enabling wfastcgi...
wfastcgi-enable

REM Configure IIS application pool
echo Configuring IIS application pool...
%windir%\system32\inetsrv\appcmd.exe set apppool /apppool.name:ProgressReport /managedRuntimeVersion:""
%windir%\system32\inetsrv\appcmd.exe set apppool /apppool.name:ProgressReport /processModel.identityType:ApplicationPoolIdentity

REM Configure IIS site
echo Configuring IIS site...
%windir%\system32\inetsrv\appcmd.exe add site /name:ProgressReport /physicalPath:"C:\inetpub\wwwroot\ProgressReport" /bindings:http/*:80:progressreport.local

REM Check URL Rewrite module installation
echo Checking URL Rewrite module...
if not exist "%windir%\System32\inetsrv\rewrite.dll" (
    echo URL Rewrite module is not installed.
    echo Please download and install from https://www.iis.net/downloads/microsoft/url-rewrite
    pause
    exit /b 1
)

echo Deployment completed.
echo Next steps:
echo 1. Add progressreport.local to hosts file
echo 2. Check authentication settings for ProgressReport site in IIS Manager
echo 3. Install SSL certificate if needed
pause 