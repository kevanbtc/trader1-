@echo off
REM ========================================
REM  TRADING ENGINE - CLEAN START
REM ========================================

echo.
echo ========================================
echo   CLEANING PYTHON CACHE
echo ========================================
echo.

REM Delete all __pycache__ directories
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM Delete all .pyc files
del /s /q *.pyc 2>nul

REM Delete all .pyo files  
del /s /q *.pyo 2>nul

echo Cache cleaned!
echo.

echo ========================================
echo   ENVIRONMENT CHECK
echo ========================================
echo.

REM Show Python version
.\.venv\Scripts\python.exe --version

echo.
echo Checking .env configuration...
echo.

REM Show key env settings
findstr /R "^TRADING_MODE= ^ENABLE_PAPER_MODE= ^ENABLE_MCP= ^ENABLE_SWARM=" .env

echo.
echo ========================================
echo   STARTING TRADING ENGINE
echo ========================================
echo.

REM Set encoding
set PYTHONIOENCODING=utf-8

REM Start trading (30 minute session)
.\.venv\Scripts\python.exe .\start_trading.py --duration 1800

echo.
echo ========================================
echo   SESSION COMPLETE
echo ========================================
echo.

pause
