@echo off
setlocal enabledelayedexpansion

cd /d "C:\Users\Admin\Downloads\AI\Anthropic\Claude Code\find cheapest items\wen-arkhas\backend"

echo =====================================================
echo Step 1: Creating virtual environment...
echo =====================================================
if exist venv (
    echo Removing existing venv...
    rmdir /s /q venv
)
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo =====================================================
echo Step 2: Upgrading pip and wheel...
echo =====================================================
python -m pip install --upgrade pip wheel setuptools

echo.
echo =====================================================
echo Step 3: Installing dependencies from requirements.txt...
echo =====================================================
pip install --only-binary :all: -r requirements.txt

echo.
echo =====================================================
echo Step 4: Running all tests (191+ tests)...
echo =====================================================
pytest tests/ -v

echo.
echo =====================================================
echo Step 5: Generating coverage report...
echo =====================================================
pytest tests/ --cov=app --cov-report=html

echo.
echo =====================================================
echo TEST RUN COMPLETE!
echo =====================================================
echo Coverage report available in: htmlcov\index.html
echo.
pause
