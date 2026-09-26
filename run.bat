@echo off
title Hand Steering Controller
echo ==================================================
echo   Starting Hand Steering Controller...
echo ==================================================

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

python main.py
pause
