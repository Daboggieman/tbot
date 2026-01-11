@echo off
echo Stopping all services...

echo Stopping Docker containers...
docker-compose down

echo Stopping host Python scripts...
echo WARNING: This will attempt to terminate ALL running 'python.exe' processes.
echo          Ensure no other critical Python applications are running.
taskkill /F /IM python.exe /T > NUL 2>&1
if %ERRORLEVEL% EQU 0 (
    echo All 'python.exe' processes terminated.
) else (
    echo No 'python.exe' processes found or unable to terminate.
)

echo All services stopped.
pause
