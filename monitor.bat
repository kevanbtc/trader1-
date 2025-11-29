@echo off
title LIVE TRADING MONITOR - Press Ctrl+C to Stop
color 0A
echo ================================================================================
echo                         LIVE TRADING MONITOR
echo ================================================================================
echo.
echo Starting continuous monitoring...
echo Press Ctrl+C to stop
echo.
echo ================================================================================
echo.

:loop
cls
echo ================================================================================
echo                    LIVE TRADING ACTIVITY [%TIME%]
echo ================================================================================
echo.

REM Show wallet balance
python -c "from web3 import Web3; w3=Web3(Web3.HTTPProvider('https://arb-mainnet.g.alchemy.com/v2/_SZloFUZ5eS1b1UVy2ODg')); usdc_abi=[{'constant':True,'inputs':[{'name':'_owner','type':'address'}],'name':'balanceOf','outputs':[{'name':'balance','type':'uint256'}],'type':'function'}]; usdc=w3.eth.contract(address='0xaf88d065e77c8cC2239327C5EDb3A432268e5831',abi=usdc_abi); wallet='0x5fc05DA8cB29f08754ac120Ab6F4F6176774b53E'; eth=w3.eth.get_balance(wallet)/1e18; usdc_bal=usdc.functions.balanceOf(wallet).call()/1e6; print(f'ETH: {eth:.6f} | USDC: {usdc_bal:.2f} | Total: ${eth*3500+usdc_bal:.2f}'); print(f'Block: {w3.eth.block_number:,} | Gas: {w3.eth.gas_price/1e9:.4f} Gwei')" 2>nul

echo.
echo ================================================================================
echo                            SESSION LOGS
echo ================================================================================
echo.

REM Show latest log entries if they exist
if exist "logs\*.json" (
    for /f %%i in ('dir /b /od logs\session_*.json 2^>nul') do set LASTLOG=%%i
    if defined LASTLOG (
        echo Latest session: !LASTLOG!
        type "logs\!LASTLOG!" 2>nul | findstr /i "opportunities trades pnl elapsed" 2>nul
    )
) else (
    echo No session logs found yet...
)

echo.
echo ================================================================================
echo Status: SCANNING FOR OPPORTUNITIES [Refresh in 10s]
echo ================================================================================
echo Live Mode Active ^| Max Position: $20 ^| Min Profit: $0.30
echo Trading Window: 8 hours ^| Scan Interval: 7 seconds
echo ================================================================================
echo.

timeout /t 10 /nobreak >nul
goto loop
