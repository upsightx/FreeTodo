#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log_dir="$repo_root/.run-logs"
mkdir -p "$log_dir"

run_bg() {
  local name="$1"
  shift
  local cmd="$*"
  echo "Starting $name..."
  "$SHELL" -lc "cd \"$repo_root\"; $cmd" >"$log_dir/$name.log" 2>&1 &
  echo $! >"$log_dir/$name.pid"
}

run_bg "phoenix" "uv run phoenix serve"
sleep 2
run_bg "lifetrace.agent_os" "uv run python -m lifetrace.agent_os"
sleep 2
run_bg "lifetrace.server" "uv run python -m lifetrace.server"
sleep 1
run_bg "frontend.dev" "pnpm -C free-todo-frontend dev"

echo "All processes started."
echo "Logs: $log_dir"
echo "Phoenix UI: http://localhost:6006"
