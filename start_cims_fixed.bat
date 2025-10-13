@echo off
chcp 65001 >nul
echo ========================================
echo CIMS - Incident Management System
echo Starting System...
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update requirements
echo Installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo Error installing requirements. Trying individual packages...
    pip install Flask==3.1.1
    pip install Flask-Login==0.6.3
    pip install requests==2.32.3
    pip install python-dotenv==1.1.0
)

REM Initialize CIMS database
echo Initializing CIMS database...
python init_cims_database.py

REM Start the application
echo Starting Flask application...
echo.
echo ========================================
echo CIMS Dashboard will be available at:
echo http://127.0.0.1:5000/incident_dashboard2
echo ========================================
echo.

python app.py

pause
