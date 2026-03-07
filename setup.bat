@echo off
REM NyayaGPT Lite - Setup Script for Windows

echo 🏛️  NyayaGPT Lite - Setup Script
echo =================================
echo.

REM Check Docker
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker found
    echo.
    echo Choose: 1) Docker  2) Manual
    set /p choice="Enter choice: "
    
    if "%choice%"=="1" (
        echo 🐳 Starting with Docker...
        docker-compose up --build -d
        echo ✅ Running at http://localhost
        exit /b 0
    )
)

REM Manual Setup
echo 📦 Manual Setup
echo.

REM Backend
echo 🐍 Setting up Backend...
cd backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
if not exist ".env" copy .env.example .env
cd ..

REM Frontend
echo ⚛️  Setting up Frontend...
cd frontend
call npm install
if not exist ".env" echo VITE_API_URL=http://localhost:8000 > .env
cd ..

echo.
echo ✅ Done! Run:
echo   Terminal 1: cd backend ^&^& venv\Scripts\activate ^&^& python main.py
echo   Terminal 2: cd frontend ^&^& npm run dev
echo.
pause
