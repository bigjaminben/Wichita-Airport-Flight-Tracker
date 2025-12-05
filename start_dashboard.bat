@echo off
REM ICT Flight Tracker - Auto Startup Script
cd /d "%~dp0"

echo Starting ICT Flight Tracker Dashboard...
echo.

REM Start the dashboard server
start "" /min .venv\Scripts\python.exe serve_prod.py

REM Wait 3 seconds
timeout /t 3 /nobreak >nul

REM Start backup manager
start "" /min .venv\Scripts\python.exe backup_manager.py

REM Wait 2 seconds
timeout /t 2 /nobreak >nul

REM Start health monitor
start "" /min .venv\Scripts\python.exe health_monitor.py

echo.
echo Dashboard started successfully!
echo Access at: http://127.0.0.1:5001/static/index.html
echo.
echo All processes running in background.
echo Check logs\ folder for activity.
echo.
timeout /t 5
exit
