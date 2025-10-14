@echo off
set /p PRIMARY_SYMBOL="Enter the primary trading symbol (e.g., EURUSD): "

if "%PRIMARY_SYMBOL%"=="" (
    echo No primary symbol entered. Exiting.
    pause
    goto :eof
)

set /p SECONDARY_SYMBOL="Enter an optional secondary trading symbol (e.g., XAUUSD, leave blank for none): "

echo Starting all services for %PRIMARY_SYMBOL% (and %SECONDARY_SYMBOL% if provided)...
call start_all.bat %PRIMARY_SYMBOL% %SECONDARY_SYMBOL%

echo Interactive startup complete.
echo You can close this window.
pause > NUL
