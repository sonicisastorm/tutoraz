@echo off
echo === TutorAZ Local Setup ===
echo.

REM Check Python version
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found. Install from python.org
    pause
    exit /b 1
)

REM Create virtual environment (isolates from system Python mess)
echo Creating virtual environment...
python -m venv venv

REM Activate it
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install deps (no psycopg2 — we use SQLite locally)
echo Installing dependencies...
pip install -r requirements.txt

REM Copy env file if not already there
if not exist .env (
    copy .env.example .env
    echo Created .env from template
)

REM Run migrations
echo Setting up database...
flask db upgrade

echo.
echo === Setup complete! ===
echo.
echo To start the server:
echo   venv\Scripts\activate
echo   python run.py
echo.
echo Then open: http://localhost:5000
pause
