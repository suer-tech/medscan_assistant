@echo off
echo Starting Medical AI Scan Assistant Development Servers...
cd /d "%~dp0"

REM Add virtual environment scripts to PATH so Python backend can use it
set PATH=%cd%\.venv\Scripts;%PATH%

REM Run the development task defined in package.json
npm run dev
pause
