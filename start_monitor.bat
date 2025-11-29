@echo off
REM ========================================
REM  LIVE TRADING MONITOR
REM ========================================

echo.
echo ========================================
echo   STARTING LIVE MONITOR
echo ========================================
echo.

REM Set encoding
set PYTHONIOENCODING=utf-8

REM Start monitor
.\.venv\Scripts\python.exe .\live_monitor.py

pause
