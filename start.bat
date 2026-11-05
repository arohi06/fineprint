
@echo off
cd /d "%~dp0"

echo Starting FinePrint...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Please create the .venv environment first.
    pause
    exit /b 1
)

echo Using project virtual environment...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt

if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"

".venv\Scripts\python.exe" run.py

echo.
echo FinePrint has stopped.
pause
