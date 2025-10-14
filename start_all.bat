@echo off
set PRIMARY_SYMBOL=%1
set SECONDARY_SYMBOL=%2

if "%PRIMARY_SYMBOL%"=="" (
    echo Usage: start_all.bat ^<PRIMARY_SYMBOL^> [SECONDARY_SYMBOL]
    echo Example: start_all.bat EURUSD
    echo Example: start_all.bat EURUSD XAUUSD
    goto :eof
)

echo Running MT5 connection check...
python mt5_checker.py
if %ERRORLEVEL% NEQ 0 (
    echo MT5 connection check failed. Aborting startup.
    pause
    goto :eof
)
echo MT5 connection check passed.

echo Starting data_downloader_api.py in background...
start /b python data_downloader_api.py
timeout /t 2 /nobreak > NUL

echo Starting Docker services (RabbitMQ, InfluxDB, PostgreSQL)...
docker-compose up -d

echo Waiting for RabbitMQ to be ready...
:WAIT_FOR_RABBITMQ
    timeout /t 5 /nobreak > NUL
    netstat -an | findstr "0.0.0.0:5672" > NUL
    if %ERRORLEVEL% NEQ 0 (
        echo RabbitMQ not yet ready, waiting...
        goto :WAIT_FOR_RABBITMQ
    )
echo RabbitMQ is ready.

set MT5_WATCHDOG_SYMBOLS=%PRIMARY_SYMBOL%
if not "%SECONDARY_SYMBOL%"=="" (
    set MT5_WATCHDOG_SYMBOLS=%MT5_WATCHDOG_SYMBOLS% %SECONDARY_SYMBOL%
)
echo Starting mt5_watchdog.py for %MT5_WATCHDOG_SYMBOLS% in background (this will start mt5_bridge.py)...
start /b python mt5_watchdog.py %MT5_WATCHDOG_SYMBOLS%
timeout /t 5 /nobreak > NUL

echo Starting mt5_order_executor.py in background...
start /b python mt5_order_executor.py
timeout /t 2 /nobreak > NUL

set BOT_COMMAND=docker-compose exec bot python main.py start-trading-session %PRIMARY_SYMBOL%
if not "%SECONDARY_SYMBOL%"=="" (
    set BOT_COMMAND=%BOT_COMMAND% --secondary-symbol %SECONDARY_SYMBOL%
)
echo Starting bot trading session for %PRIMARY_SYMBOL% (and %SECONDARY_SYMBOL% if provided)...
%BOT_COMMAND%

echo All services started.
echo You can check logs with: docker-compose logs -f bot
echo To stop all services: docker-compose down
