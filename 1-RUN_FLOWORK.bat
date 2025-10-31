@echo off
TITLE FLOWORK - Docker Launcher
cls
echo =================================================================
echo        FLOWORK DOCKER STACK LAUNCHER
echo =================================================================
echo.
echo --- [STEP 1/4] Ensuring Docker Desktop is running ---
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not running. Please start it and run this script again.
    pause
    exit /b 1
)
echo [SUCCESS] Docker Desktop is active.
echo.
echo --- [STEP 2/4] Stopping any old running containers (Safe Mode) ---
docker-compose down
echo [SUCCESS] Old containers stopped.
echo.
echo --- [STEP 3/4] Building (or rebuilding) and starting all services ---
echo (The container's internal command now handles all initial setup)
docker-compose up --build -d
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose failed to build or start containers.
    pause
    exit /b 1
)
echo.
echo.
docker-compose ps
echo.
echo -----------------------------------------------------------
echo [INFO] Main GUI is accessible at https://flowork.cloud
echo ------------------------------------------------------------
echo.
echo [IMPORTANT!] If the Core Engine still fails to authenticate after a few minutes,
echo              please check the logs using 'docker-compose logs core'.
echo.
echo --- [AUTO-LOG] Displaying Cloudflare Tunnel status (last 50 lines)... ---
echo.
docker-compose logs --tail="50" cloudflared
echo.
echo -----------------------------------------------------------------
echo.
echo --- [ AUTO-LOG (PENTING) ] MENCARI PRIVATE KEY ANDA... ---
echo.
echo    Your Login Private Key should appear below (inside the warning box):
echo.
docker compose logs gateway | findstr /C:"!!! YOUR LOGIN PRIVATE KEY IS" /C:"0x"
echo.
echo -----------------------------------------------------------------
echo [INFO] Copy the Private Key line above (it already includes '0x') and use it to log in.
echo.
pause