@echo off
setlocal enabledelayedexpansion
REM FreeTodo 一键停止脚本
REM 根据端口杀掉所有相关服务进程

echo ================================
echo    FreeTodo 一键停止
echo ================================
echo.

call :kill_by_port 6006 Phoenix
call :kill_by_port 8200 AgentOS
call :kill_by_port 8001 Backend
call :kill_by_port 3001 Frontend
call :kill_by_port 4040 ngrok

echo.
echo ================================
echo    所有服务已停止
echo ================================
echo.
pause
endlocal
goto :eof

:kill_by_port
setlocal enabledelayedexpansion
set "PORT=%~1"
set "NAME=%~2"
set "KILLED="

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    if "%%a" NEQ "0" if "%%a" NEQ "" (
        set "SKIP="
        for %%k in (!KILLED!) do (
            if "%%k"=="%%a" set "SKIP=1"
        )
        if not defined SKIP (
            echo [停止] %NAME% (端口 %PORT%, PID %%a^)
            taskkill /F /PID %%a
            set "KILLED=!KILLED! %%a"
        )
    )
)

if not defined KILLED (
    echo [跳过] %NAME% (端口 %PORT% 未占用^)
)

endlocal
goto :eof
