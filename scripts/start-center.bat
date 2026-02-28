@echo off
chcp 65001 >nul 2>nul
REM ================================================================
REM  LifeTrace Center Node - One-click Startup
REM  Phoenix -> AgentOS -> Backend(center) -> Frontend -> cpolar x2
REM ================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0\.."
set "REPO_ROOT=%cd%"
set "LOG_DIR=%REPO_ROOT%\.run-logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM ================================================================
REM  Load local config (if exists)
REM ================================================================
if exist "%~dp0local-env.bat" (
    call "%~dp0local-env.bat"
)

REM Fallback defaults (override in scripts/local-env.bat)
if "%CPOLAR_BACKEND_DOMAIN%"=="" set "CPOLAR_BACKEND_DOMAIN=YOUR_BACKEND_SUBDOMAIN"
if "%CPOLAR_FRONTEND_DOMAIN%"=="" set "CPOLAR_FRONTEND_DOMAIN=YOUR_FRONTEND_SUBDOMAIN"
REM Support per-tunnel suffix (cpolar may assign .cpolar.cn and .cpolar.top to different tunnels)
if "%CPOLAR_BACKEND_SUFFIX%"=="" if "%CPOLAR_DOMAIN_SUFFIX%"=="" set "CPOLAR_BACKEND_SUFFIX=cpolar.cn"
if "%CPOLAR_FRONTEND_SUFFIX%"=="" if "%CPOLAR_DOMAIN_SUFFIX%"=="" set "CPOLAR_FRONTEND_SUFFIX=cpolar.cn"
if "%CPOLAR_BACKEND_SUFFIX%"=="" set "CPOLAR_BACKEND_SUFFIX=%CPOLAR_DOMAIN_SUFFIX%"
if "%CPOLAR_FRONTEND_SUFFIX%"=="" set "CPOLAR_FRONTEND_SUFFIX=%CPOLAR_DOMAIN_SUFFIX%"

REM Ports
set "BACKEND_PORT=8001"
set "FRONTEND_PORT=3001"

REM ================================================================
REM  Derive public URLs
REM ================================================================
set "BACKEND_PUBLIC_URL=https://%CPOLAR_BACKEND_DOMAIN%.%CPOLAR_BACKEND_SUFFIX%"
set "FRONTEND_PUBLIC_URL=https://%CPOLAR_FRONTEND_DOMAIN%.%CPOLAR_FRONTEND_SUFFIX%"

REM ================================================================
REM  Validate config
REM ================================================================
if "%CPOLAR_BACKEND_DOMAIN%"=="YOUR_BACKEND_SUBDOMAIN" (
    echo [ERROR] Please create scripts\local-env.bat with your cpolar subdomains.
    echo         See scripts\local-env.bat.example or edit this file directly.
    echo.
    pause
    exit /b 1
)

echo ================================================
echo    LifeTrace Center Node Startup
echo ================================================
echo.
echo Backend local:   http://0.0.0.0:%BACKEND_PORT%
echo Backend public:  %BACKEND_PUBLIC_URL%
echo Frontend local:  http://0.0.0.0:%FRONTEND_PORT%
echo Frontend public: %FRONTEND_PUBLIC_URL%
echo.

REM ================================================================
REM  1. Start Phoenix (observability tracing)
REM ================================================================
echo [1/6] Starting Phoenix (observability)...
start "LifeTrace Phoenix" cmd /k "pushd %REPO_ROOT% && uv run phoenix serve"
echo Waiting for Phoenix (2s)...
timeout /t 2 /nobreak >nul

REM ================================================================
REM  2. Start AgentOS (Agno agent framework, must start before backend)
REM ================================================================
echo [2/6] Starting AgentOS...
start "LifeTrace AgentOS" cmd /k "pushd %REPO_ROOT% && uv run python -m lifetrace.agent_os"
echo Waiting for AgentOS (2s)...
timeout /t 2 /nobreak >nul

REM ================================================================
REM  3. Start backend (center mode)
REM ================================================================
echo [3/6] Starting LifeTrace Server (center mode)...
start "LifeTrace Center Backend" cmd /k "pushd %REPO_ROOT% && uv run python -m lifetrace.server --role center"
echo Waiting for backend (5s)...
timeout /t 5 /nobreak >nul

REM ================================================================
REM  4. Build and start frontend (NEXT_PUBLIC_API_URL -> cpolar URL)
REM ================================================================
echo [4/6] Building frontend (API = %BACKEND_PUBLIC_URL%)...
start "LifeTrace Center Frontend" cmd /k "pushd %REPO_ROOT%\free-todo-frontend && set NEXT_PUBLIC_API_URL=%BACKEND_PUBLIC_URL%&& pnpm build:frontend:web && pnpm start --port %FRONTEND_PORT% --hostname 0.0.0.0"
echo Waiting for frontend build (~30s)...
timeout /t 30 /nobreak >nul

REM ================================================================
REM  5. Start cpolar backend tunnel
REM ================================================================
echo [5/6] Starting cpolar backend tunnel = %BACKEND_PUBLIC_URL%
start "LifeTrace cpolar Backend" cmd /k "cpolar http %BACKEND_PORT% -subdomain=%CPOLAR_BACKEND_DOMAIN%"
timeout /t 2 /nobreak >nul

REM ================================================================
REM  6. Start cpolar frontend tunnel
REM ================================================================
echo [6/6] Starting cpolar frontend tunnel = %FRONTEND_PUBLIC_URL%
start "LifeTrace cpolar Frontend" cmd /k "cpolar http %FRONTEND_PORT% -subdomain=%CPOLAR_FRONTEND_DOMAIN%"

REM ================================================================
REM  Done
REM ================================================================
echo.
echo ================================================
echo    Center Node Started (6 windows)
echo ================================================
echo.
echo Services:
echo   Phoenix:      http://127.0.0.1:6006
echo   AgentOS:      http://127.0.0.1:8200
echo   Backend:      http://0.0.0.0:%BACKEND_PORT%
echo   Frontend:     http://0.0.0.0:%FRONTEND_PORT%
echo.
echo Public access:
echo   Frontend UI:  %FRONTEND_PUBLIC_URL%
echo   Backend API:  %BACKEND_PUBLIC_URL%
echo.
echo Sensor startup command:
echo   python -m lifetrace.sensor --center-url %BACKEND_PUBLIC_URL%
echo.
echo Tip: close each window to stop its service.
echo.
pause
endlocal
