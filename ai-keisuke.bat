@echo off
REM AI Darari-nu Bot Startup Script (Windows - English)
REM This script automatically activates virtual environment and runs the bot

echo ==============================
echo   AI Darari-nu Bot Starting...
echo ==============================

REM Change to script directory
cd /d %~dp0

REM Check if virtual environment exists
if not exist "ai-darari-nu-env\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Please create virtual environment with one of these commands:
    echo.
    echo   python -m venv ai-darari-nu-env
    echo   python3 -m venv ai-darari-nu-env
    echo   py -m venv ai-darari-nu-env
    echo.
    echo Creating virtual environment automatically...
    
    REM Try different Python commands
    python -m venv ai-darari-nu-env 2>nul
    if not exist "ai-darari-nu-env\Scripts\activate.bat" (
        python3 -m venv ai-darari-nu-env 2>nul
    )
    if not exist "ai-darari-nu-env\Scripts\activate.bat" (
        py -m venv ai-darari-nu-env 2>nul
    )
    
    if not exist "ai-darari-nu-env\Scripts\activate.bat" (
        echo.
        echo [ERROR] Failed to create virtual environment.
        echo Please install Python 3.8 or higher and try again.
        echo.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created successfully!
)

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Please create .env file with:
    echo DISCORD_BOT_TOKEN=your_discord_bot_token_here
    echo OPENAI_API_KEY=your_openai_api_key_here
    echo.
    pause
    exit /b 1
)

echo [INFO] Activating virtual environment...
call ai-darari-nu-env\Scripts\activate.bat

echo [INFO] Checking dependencies...
pip install -r requirements.txt --quiet

echo [INFO] Starting AI Darari-nu Bot with auto-restart...
echo [INFO] Press Ctrl+C to stop completely
echo.

:restart_loop
echo [%date% %time%] Starting AI Darari-nu Bot...
python main.py

echo.
echo [%date% %time%] Bot has stopped - Restarting in 3 seconds...
echo [INFO] Press Ctrl+C now to stop, or wait for automatic restart...
timeout /t 3
goto restart_loop