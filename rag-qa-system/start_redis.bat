@echo off
echo Starting Redis Server for RAG QA System...
echo.

REM Check if Redis is already running
netstat -an | findstr :6379 > nul
if %errorlevel% == 0 (
    echo Redis is already running on port 6379
    pause
    exit /b
)

REM Download and extract Redis if not exists
if not exist "redis\redis-server.exe" (
    echo Downloading Redis...
    mkdir redis 2>nul
    
    REM You can download Redis from: https://github.com/tporadowski/redis/releases
    echo Please download Redis from: https://github.com/tporadowski/redis/releases
    echo Extract to the 'redis' folder and run this script again.
    pause
    exit /b
)

REM Start Redis server
echo Starting Redis server...
cd redis
redis-server.exe ..\redis\redis.conf

pause