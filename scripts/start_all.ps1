Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
$shell = if ($pwsh) { "pwsh" } else { "powershell" }

Start-Process -FilePath $shell -WorkingDirectory $repoRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    "uv run python -m lifetrace.server"
)

Start-Sleep -Seconds 1

Start-Process -FilePath $shell -WorkingDirectory $repoRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    "uv run python -m lifetrace.agent_os"
)

Start-Sleep -Seconds 1

Start-Process -FilePath $shell -WorkingDirectory $repoRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    "pnpm -C free-todo-frontend dev"
)
