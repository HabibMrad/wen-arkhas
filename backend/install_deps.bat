@echo off
cd /d "C:\Users\Admin\Downloads\AI\Anthropic\Claude Code\find cheapest items\wen-arkhas\backend"

REM Create fresh venv
if exist venv (
    rmdir /s /q venv
)
python -m venv venv

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip wheel

REM Install requirements
pip install -r requirements.txt

echo.
echo ============================================
echo Installation complete!
echo ============================================
echo.
pause
