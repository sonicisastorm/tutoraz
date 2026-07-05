@echo off
echo === TutorAZ Local Setup ===
echo.

python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found. Install from python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv

echo Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo Installing dependencies...
venv\Scripts\pip.exe install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo Created .env from template
)

echo Setting up database...
venv\Scripts\python.exe -m flask db upgrade

echo.
echo === Setup complete! ===
echo.
echo IMPORTANT: Open .env and add your Stripe TEST keys before using course payments:
echo   STRIPE_SECRET_KEY=sk_test_...
echo   STRIPE_PUBLISHABLE_KEY=pk_test_...
echo   Get them free at https://dashboard.stripe.com/test/apikeys
echo.
echo HOW TO START THE SERVER:
echo.
echo   If using CMD or PowerShell:
echo     venv\Scripts\activate
echo     python run.py
echo.
echo   If using Git Bash (MINGW64):
echo     source venv/Scripts/activate
echo     python run.py
echo.
echo Then open: http://localhost:5000
echo.
pause
