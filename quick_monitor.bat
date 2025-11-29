@echo off
REM Quick launcher for AWS trading monitors
REM Choose your view

echo.
echo ========================================
echo   AWS TRADING ENGINE - MONITORING
echo ========================================
echo.
echo Choose your view:
echo.
echo [1] Mission Control (Unified Dashboard)
echo [2] Live Opportunity Ledger
echo [3] Process Status Only
echo [4] Recent Activity Stream
echo [5] Exit
echo.
set /p choice="Enter choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Starting Mission Control Dashboard...
    python aws_mission_control.py
)

if "%choice%"=="2" (
    echo.
    echo Connecting to opportunity ledger...
    ssh -i "C:\Users\Kevan\donk x\donkx-prod.pem" ubuntu@54.158.163.67 "tail -f ~/apex/logs/opportunity_ledger.log"
)

if "%choice%"=="3" (
    echo.
    echo Checking process status...
    ssh -i "C:\Users\Kevan\donk x\donkx-prod.pem" ubuntu@54.158.163.67 "ps aux | grep 'start_trading' | grep -v grep && echo '---' && sudo supervisorctl status"
    pause
)

if "%choice%"=="4" (
    echo.
    echo Streaming recent activity...
    ssh -i "C:\Users\Kevan\donk x\donkx-prod.pem" ubuntu@54.158.163.67 "tail -50 ~/apex/logs/opportunity_ledger.log && echo '--- LIVE STREAM ---' && tail -f ~/apex/logs/opportunity_ledger.log"
)

if "%choice%"=="5" exit
