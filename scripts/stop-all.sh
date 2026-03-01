#!/bin/bash
# FreeTodo 一键停止脚本
# 根据端口杀掉所有相关服务进程

set -e

# 服务端口列表
PORTS=(
    6006   # Phoenix（可观测性）
    8200   # AgentOS
    8001   # 后端 Backend
    3001   # 前端 Frontend
    4040   # ngrok 控制台
)

echo "================================"
echo "   FreeTodo 一键停止"
echo "================================"
echo ""

kill_by_port() {
    local port=$1
    local name=$2

    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        # Windows (Git Bash / MSYS2)
        pid=$(netstat -ano 2>/dev/null | grep ":$port " | grep "LISTENING" | awk '{print $5}' | head -1)
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            echo "[停止] $name (端口 $port, PID $pid)"
            taskkill //F //PID "$pid" 2>/dev/null || true
        else
            echo "[跳过] $name (端口 $port 未占用)"
        fi
    else
        # Linux / macOS
        pid=$(lsof -ti tcp:$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            echo "[停止] $name (端口 $port, PID $pid)"
            kill -9 $pid 2>/dev/null || true
        else
            echo "[跳过] $name (端口 $port 未占用)"
        fi
    fi
}

# 按端口停止服务
kill_by_port 6006 "Phoenix"
kill_by_port 8200 "AgentOS"
kill_by_port 8001 "Backend"
kill_by_port 3001 "Frontend"
kill_by_port 4040 "ngrok"

echo ""
echo "================================"
echo "   所有服务已停止"
echo "================================"
