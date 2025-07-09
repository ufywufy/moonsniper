@echo off
echo Installing Python packages from requirements.txt...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Failed to install requirements. Make sure Python and pip are installed and added to PATH.
    pause
    exit /b 1
)

echo All dependencies installed!
pause