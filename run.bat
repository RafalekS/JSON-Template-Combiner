@echo off
title JSON Template Combiner
echo Starting JSON Template Combiner...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher and try again
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade requirements
echo Installing requirements...
pip install -r requirements.txt

REM Check if installation was successful
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

REM Run the application
echo.
echo Starting JSON Template Combiner...
echo.
python main.py

REM Deactivate virtual environment when done
deactivate

echo.
echo Application closed. Press any key to exit...
pause >nul
