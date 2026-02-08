@echo off
REM FreeTodo 一键启动脚本（三个独立窗口）

echo ================================
echo    FreeTodo 一键启动
echo ================================
echo.

REM 启动后端（新窗口）
echo [1/3] 启动后端...
start "FreeTodo Backend" cmd /k "cd /d "%~dp0" & uv run python -m lifetrace.server"
echo 等待后端启动（5秒）...
timeout /t 5 /nobreak >nul

REM 启动前端（新窗口）
echo [2/3] 启动前端...
start "FreeTodo Frontend" cmd /k "cd /d "%~dp0" & cd free-todo-frontend & pnpm dev"
echo 等待前端启动（3秒）...
timeout /t 3 /nobreak >nul

REM 启动 ngrok（新窗口）
echo [3/3] 启动 ngrok...
start "FreeTodo ngrok" cmd /k "cd /d "%~dp0" & C:\Users\25048\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe http 8001"

echo.
echo ================================
echo    所有服务已启动（独立窗口）
echo ================================
echo.
echo 后端: http://127.0.0.1:8001
echo 前端: http://127.0.0.1:3001 (等待启动...)
echo ngrok 控制台: http://127.0.0.1:4040
echo.
echo 关闭窗口即可停止对应服务
echo.
pause
