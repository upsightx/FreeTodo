param(
    [string]$Dir = $env:LIFETRACE_DIR,
    [string]$Repo = $env:LIFETRACE_REPO,
    [Alias("r")]
    [string]$Ref = $env:LIFETRACE_REF,
    [Alias("m")]
    [string]$Mode = $env:LIFETRACE_MODE,
    [string]$Variant = $env:LIFETRACE_VARIANT,
    [string]$Frontend = $env:LIFETRACE_FRONTEND,
    [string]$Backend = $env:LIFETRACE_BACKEND,
    [string]$Run = $env:LIFETRACE_RUN
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$frontendSet = $PSBoundParameters.ContainsKey("Frontend") -or [bool]$env:LIFETRACE_FRONTEND
$variantSet = $PSBoundParameters.ContainsKey("Variant") -or [bool]$env:LIFETRACE_VARIANT
$dirSet = $PSBoundParameters.ContainsKey("Dir") -or [bool]$env:LIFETRACE_DIR
$modeSet = $PSBoundParameters.ContainsKey("Mode") -or [bool]$env:LIFETRACE_MODE
$backendSet = $PSBoundParameters.ContainsKey("Backend") -or [bool]$env:LIFETRACE_BACKEND

if (-not $Repo) {
    $Repo = "https://github.com/FreeU-group/FreeTodo.git"
}
if (-not $Ref) {
    $Ref = "main"
}
if (-not $Mode) {
    $Mode = "tauri"
}
if (-not $Variant) {
    $Variant = "web"
}
if (-not $Frontend) {
    $Frontend = "build"
}
if (-not $Backend) {
    $Backend = "script"
}
if (-not $Run) {
    $Run = "1"
}

function Prompt-Choice {
    param(
        [string]$Label,
        [string[]]$Choices,
        [string]$Default
    )
    Write-Host $Label
    for ($i = 0; $i -lt $Choices.Count; $i++) {
        Write-Host "  $($i + 1)) $($Choices[$i])"
    }
    $input = Read-Host "Select [default: $Default]"
    if ([string]::IsNullOrWhiteSpace($input)) {
        return $Default
    }
    if ($input -match '^\d+$') {
        $index = [int]$input - 1
        if ($index -ge 0 -and $index -lt $Choices.Count) {
            return $Choices[$index]
        }
    } else {
        foreach ($choice in $Choices) {
            if ($choice -eq $input) {
                return $choice
            }
        }
    }
    Write-Host "Invalid choice. Using default: $Default"
    return $Default
}

if (-not $dirSet) {
    $repoName = [IO.Path]::GetFileNameWithoutExtension($Repo)
    $Dir = $repoName
}

if (-not $variantSet) {
    $Variant = Prompt-Choice "Select UI variant:" @("web", "island") "web"
}
if (-not $backendSet) {
    $Backend = Prompt-Choice "Select backend runtime:" @("script", "pyinstaller") "script"
}
if (-not $modeSet) {
    $Mode = Prompt-Choice "Select app mode:" @("tauri", "electron", "web") "tauri"
}

if ($Mode -eq "island") {
    $Mode = "tauri"
    $Variant = "island"
    $variantSet = $true
}

if ($Variant -eq "island" -and $Mode -eq "web") {
    Write-Host "Variant 'island' is not supported in web mode. Switching mode to tauri."
    $Mode = "tauri"
}

if ($Mode -eq "web" -and $Variant -ne "web") {
    throw "Variant '$Variant' is not supported in web mode."
}

$validModes = @("web", "tauri", "electron")
if ($validModes -notcontains $Mode) {
    throw "Invalid mode: $Mode"
}

$validVariants = @("web", "island")
if ($validVariants -notcontains $Variant) {
    throw "Invalid variant: $Variant"
}

$validFrontend = @("build", "dev")
if ($validFrontend -notcontains $Frontend) {
    throw "Invalid frontend action: $Frontend"
}

$validBackend = @("script", "pyinstaller")
if ($validBackend -notcontains $Backend) {
    throw "Invalid backend runtime: $Backend"
}

if ($Backend -eq "pyinstaller" -and -not $frontendSet) {
    $Frontend = "build"
}

if ($Frontend -eq "dev" -and $Backend -eq "pyinstaller") {
    throw "backend=pyinstaller is only supported with frontend=build."
}

if ($Mode -eq "tauri" -and $Frontend -eq "build" -and $Variant -eq "island") {
    Write-Host "Island packaging is not supported yet. Switching variant to web for build."
    $Variant = "web"
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$missingDeps = New-Object System.Collections.Generic.List[object]

function Add-MissingDep {
    param(
        [string]$Name,
        [string]$Hint,
        [string]$WingetId = ""
    )
    $missingDeps.Add([pscustomobject]@{
            Name     = $Name
            Hint     = $Hint
            WingetId = $WingetId
        })
}

function Refresh-Path {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Install-MissingDeps {
    if ($missingDeps.Count -eq 0) {
        return
    }

    $wingetDeps = $missingDeps | Where-Object { $_.WingetId }
    if ($wingetDeps -and -not (Test-Command "winget")) {
        Install-Winget | Out-Null
    }
    if ($wingetDeps -and (Test-Command "winget")) {
        foreach ($dep in $wingetDeps) {
            Write-Host "Installing $($dep.Name) with winget..."
            winget install --id $($dep.WingetId) -e --accept-package-agreements --accept-source-agreements
        }
        Refresh-Path
    }
}

function Filter-MissingDeps {
    $remaining = New-Object System.Collections.Generic.List[object]
    foreach ($dep in $missingDeps) {
        if (-not (Test-Command $dep.Name)) {
            $remaining.Add($dep)
        }
    }
    $script:missingDeps = $remaining
}

function Show-MissingDeps {
    if ($missingDeps.Count -eq 0) {
        return
    }

    Write-Host "Missing required dependencies:" -ForegroundColor Red
    foreach ($dep in $missingDeps) {
        Write-Host "- $($dep.Name): $($dep.Hint)"
    }

    $wingetDeps = $missingDeps | Where-Object { $_.WingetId }
    if ($wingetDeps -and (Test-Command "winget")) {
        Write-Host "Install with winget:"
        foreach ($dep in $wingetDeps) {
            Write-Host "  winget install --id $($dep.WingetId) -e --accept-package-agreements --accept-source-agreements"
        }
    } elseif ($wingetDeps) {
        Write-Host "winget not found. Install App Installer from Microsoft Store or from https://aka.ms/getwinget"
    }

    throw "Missing required dependencies. Install them and retry."
}

function Invoke-HookSetup {
    $hookScript = Join-Path (Get-Location).Path "scripts\\setup_hooks_here.ps1"
    if (Test-Path -LiteralPath $hookScript) {
        try {
            & $hookScript
        } catch {
            Write-Warning "Failed to configure git hooks: $($_.Exception.Message)"
        }
    }
}

# 默认端口与范围（与 dev-with-auto-port.js、lifetrace 后端及 AgentOS 配置一致）
$script:DEFAULT_BACKEND_PORT = 8001
$script:DEFAULT_FRONTEND_PORT = 3001
$script:DEFAULT_AGENTOS_PORT = 8200
$script:BACKEND_PORT_MIN = 8000
$script:BACKEND_PORT_MAX = 8099
$script:FRONTEND_PORT_MIN = 3001
$script:FRONTEND_PORT_MAX = 3199
$script:AGENTOS_PORT_MIN = 8200
$script:AGENTOS_PORT_MAX = 8299

function Test-PortAvailable {
    param([int]$Port)
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Get-RandomAvailablePort {
    param(
        [int]$MinPort,
        [int]$MaxPort,
        [int[]]$ExcludePorts = @(),
        [int]$MaxAttempts = 150
    )
    $candidates = [System.Collections.ArrayList]::new()
    for ($p = $MinPort; $p -le $MaxPort; $p++) {
        if ($ExcludePorts -notcontains $p) {
            [void]$candidates.Add($p)
        }
    }
    if ($candidates.Count -eq 0) {
        throw "No port candidates in range $MinPort-$MaxPort (excluding $($ExcludePorts -join ','))"
    }
    $shuffled = $candidates | Sort-Object { Get-Random }
    $toTry = [Math]::Min($MaxAttempts, $shuffled.Count)
    for ($i = 0; $i -lt $toTry; $i++) {
        $port = $shuffled[$i]
        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }
    throw "Cannot find available port in range $MinPort-$MaxPort after $MaxAttempts random attempts"
}

function Resolve-DevPorts {
    $backendPort = $script:DEFAULT_BACKEND_PORT
    $frontendPort = $script:DEFAULT_FRONTEND_PORT
    $agentosPort = $script:DEFAULT_AGENTOS_PORT
    $backendNeedRandom = -not (Test-PortAvailable -Port $backendPort)
    $frontendNeedRandom = -not (Test-PortAvailable -Port $frontendPort)
    $agentosNeedRandom = -not (Test-PortAvailable -Port $agentosPort)
    if ($backendNeedRandom -or $frontendNeedRandom -or $agentosNeedRandom) {
        Write-Host "Detected port conflict, allocating random available ports..."
        if ($backendNeedRandom) {
            $excludeForBackend = @()
            if (-not $frontendNeedRandom) { $excludeForBackend += $frontendPort }
            if (-not $agentosNeedRandom) { $excludeForBackend += $agentosPort }
            $backendPort = Get-RandomAvailablePort `
                -MinPort $script:BACKEND_PORT_MIN -MaxPort $script:BACKEND_PORT_MAX `
                -ExcludePorts $excludeForBackend
            Write-Host "  Backend port $($script:DEFAULT_BACKEND_PORT) in use, using $backendPort"
        }
        if ($frontendNeedRandom) {
            $frontendPort = Get-RandomAvailablePort `
                -MinPort $script:FRONTEND_PORT_MIN -MaxPort $script:FRONTEND_PORT_MAX `
                -ExcludePorts @($backendPort, $agentosPort)
            Write-Host "  Frontend port $($script:DEFAULT_FRONTEND_PORT) in use, using $frontendPort"
        }
        if ($agentosNeedRandom) {
            $agentosPort = Get-RandomAvailablePort `
                -MinPort $script:AGENTOS_PORT_MIN -MaxPort $script:AGENTOS_PORT_MAX `
                -ExcludePorts @($backendPort, $frontendPort)
            Write-Host "  AgentOS port $($script:DEFAULT_AGENTOS_PORT) in use, using $agentosPort"
        }
        $allPorts = @($backendPort, $frontendPort, $agentosPort)
        if ($allPorts.Count -ne ($allPorts | Select-Object -Unique).Count) {
            throw "Resolved ports must differ: backend=$backendPort, frontend=$frontendPort, agentos=$agentosPort"
        }
    }
    return @{ BackendPort = $backendPort; FrontendPort = $frontendPort; AgentosPort = $agentosPort }
}

function Install-Winget {
    if (Test-Command "winget") {
        return $true
    }
    if (-not (Test-Command "Add-AppxPackage")) {
        return $false
    }
    $wingetInstallerUrl = "https://aka.ms/getwinget"
    $installerPath = Join-Path $env:TEMP "winget.msixbundle"
    try {
        Write-Host "winget not found. Attempting to install App Installer..."
        Invoke-WebRequest -Uri $wingetInstallerUrl -OutFile $installerPath
        Add-AppxPackage -Path $installerPath
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Automatic winget install failed."
        return $false
    }
    return (Test-Command "winget")
}

function Get-LatestFile {
    param(
        [string]$Path,
        [string]$Filter
    )
    if (-not (Test-Path $Path)) {
        return $null
    }
    $file = Get-ChildItem -Path $Path -Filter $Filter -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($file) {
        return $file.FullName
    }
    return $null
}

function Find-TauriArtifact {
    param(
        [string]$FrontendDir,
        [string]$Variant,
        [string]$Backend
    )
    $artifactBase = Join-Path $FrontendDir "dist-artifacts\tauri\$Variant\$Backend"
    $bundleDir = Join-Path $FrontendDir "src-tauri\target\release\bundle"
    $binaryDir = Join-Path $FrontendDir "src-tauri\target\release"
    $artifact = Get-LatestFile $binaryDir "*.exe"
    if ($artifact) {
        return $artifact
    }
    $artifact = Get-LatestFile $artifactBase "*.exe"
    if (-not $artifact) {
        $artifact = Get-LatestFile $bundleDir "*.exe"
    }
    if (-not $artifact) {
        $artifact = Get-LatestFile $bundleDir "*.msi"
    }
    return $artifact
}

function Find-ElectronArtifact {
    param(
        [string]$FrontendDir,
        [string]$Variant,
        [string]$Backend
    )
    $artifactBase = Join-Path $FrontendDir "dist-artifacts\electron\$Variant\$Backend"
    $artifact = Get-LatestFile $artifactBase "*.exe"
    if (-not $artifact) {
        $artifact = Get-LatestFile $artifactBase "*.msi"
    }
    return $artifact
}

function Start-BuiltApp {
    param([string]$ArtifactPath)
    if (-not $ArtifactPath) {
        return $false
    }
    Write-Host "Launching built app: $ArtifactPath"
    Start-Process -FilePath $ArtifactPath | Out-Null
    return $true
}

$pythonCmd = $env:PYTHON_BIN
if (-not $pythonCmd) {
    if (Test-Command "python") {
        $pythonCmd = "python"
    } elseif (Test-Command "python3") {
        $pythonCmd = "python3"
    } else {
        Add-MissingDep "python" "Python 3.12+ not found. Install Python and retry." "Python.Python.3.12"
    }
} elseif (-not (Test-Command $pythonCmd)) {
    Add-MissingDep "python" "Python 3.12+ not found. Install Python and retry." "Python.Python.3.12"
}

if (-not (Test-Command "git")) {
    Add-MissingDep "git" "Install Git and retry." "Git.Git"
}
if (-not (Test-Command "node")) {
    Add-MissingDep "node" "Install Node.js 20+ and retry." "OpenJS.NodeJS.LTS"
}

if ($Mode -eq "tauri") {
    if (-not (Test-Command "cargo")) {
        Add-MissingDep "cargo" "Install Rust (rustup) and retry, or set LIFETRACE_MODE=web." "Rustlang.Rustup"
    }
}

Install-MissingDeps
Filter-MissingDeps
Show-MissingDeps

if (-not $pythonCmd -or -not (Test-Command $pythonCmd)) {
    if (Test-Command "python") {
        $pythonCmd = "python"
    } elseif (Test-Command "python3") {
        $pythonCmd = "python3"
    } else {
        throw "Python 3.12+ not found after installation. Reopen your terminal and retry."
    }
}

if (-not (Test-Command "uv")) {
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

if (-not (Test-Command "pnpm")) {
    $pnpmInstalled = $false
    if (Test-Command "corepack") {
        try {
            corepack enable
            corepack prepare pnpm@latest --activate
            $pnpmInstalled = Test-Command "pnpm"
        } catch {
            Write-Host "corepack activation failed. Falling back to pnpm install script."
        }
    }
    if (-not $pnpmInstalled -and (Test-Command "npm")) {
        try {
            npm install -g pnpm
            Refresh-Path
            $pnpmInstalled = Test-Command "pnpm"
        } catch {
            Write-Host "npm global install failed. Falling back to pnpm install script."
        }
    }
    if (-not $pnpmInstalled) {
        Write-Host "Installing pnpm via install script..."
        $env:PNPM_HOME = Join-Path $env:USERPROFILE ".local\share\pnpm"
        if (-not (Test-Path $env:PNPM_HOME)) {
            New-Item -ItemType Directory -Force -Path $env:PNPM_HOME | Out-Null
        }
        $env:Path = "$env:PNPM_HOME;$env:Path"
        try {
            irm https://get.pnpm.io/install.ps1 | iex
        } catch {
            throw "pnpm install script failed. Install pnpm manually and retry."
        }
        $pnpmInstalled = Test-Command "pnpm"
    }
    if (-not $pnpmInstalled) {
        throw "pnpm not found after installation. Reopen your terminal and retry."
    }
}

$repoReady = $false
$depsReady = $false
if (Test-Path $Dir) {
    if (-not (Test-Path (Join-Path $Dir ".git"))) {
        throw "Target path '$Dir' exists and is not a git repo. Set LIFETRACE_DIR to a new folder."
    }
    Set-Location $Dir
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        throw "Repository has local changes. Commit or stash and retry."
    }
    git fetch --depth 1 "$Repo" "$Ref"
    $headSha = git rev-parse HEAD
    $remoteSha = git rev-parse FETCH_HEAD
    if ($headSha -eq $remoteSha) {
        $repoReady = $true
    }
} else {
    git clone --depth 1 --branch "$Ref" "$Repo" "$Dir"
    Set-Location $Dir
}

$venvReady = Test-Path (Join-Path (Get-Location).Path ".venv")
$frontendModulesReady = Test-Path (Join-Path (Get-Location).Path "free-todo-frontend\node_modules")
$depsReady = $venvReady -and $frontendModulesReady

if (-not $repoReady -or -not $depsReady) {
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        throw "Repository has local changes. Commit or stash and retry."
    }
    git fetch --depth 1 "$Repo" "$Ref"
    git checkout -q -B "$Ref" FETCH_HEAD
    uv sync
    $venvReady = Test-Path (Join-Path (Get-Location).Path ".venv")
    $frontendModulesReady = Test-Path (Join-Path (Get-Location).Path "free-todo-frontend\node_modules")
    $depsReady = $venvReady -and $frontendModulesReady
} else {
    Write-Host "Repository is up to date. Skipping install steps."
}

Invoke-HookSetup

if ($Run -ne "1") {
    Write-Host "Install complete."
    exit 0
}

$devPorts = Resolve-DevPorts
$backendPort = $devPorts.BackendPort
$frontendPort = $devPorts.FrontendPort
$agentosPort = $devPorts.AgentosPort

if ($Mode -eq "web") {
    $uvPath = (Get-Command uv).Source
    $backendJob = Start-Job -ScriptBlock {
        param($RepoDir, $UvPath, $PythonCmd, $BackendPort)
        Set-Location $RepoDir
        & $UvPath run $PythonCmd -m lifetrace.server --port $BackendPort
    } -ArgumentList (Get-Location).Path, $uvPath, $pythonCmd, $backendPort

    $agentosJob = Start-Job -ScriptBlock {
        param($RepoDir, $UvPath, $PythonCmd, $AgentosPort)
        Set-Location $RepoDir
        $env:LIFETRACE__AGNO__AGENT_OS__PORT = $AgentosPort
        & $UvPath run $PythonCmd -m lifetrace.agent_os
    } -ArgumentList (Get-Location).Path, $uvPath, $pythonCmd, $agentosPort

    try {
        Set-Location (Join-Path (Get-Location).Path "free-todo-frontend")
        if (-not $frontendModulesReady) {
            pnpm install
        }
        if ($Frontend -eq "build") {
            $nextDir = Join-Path (Get-Location).Path ".next"
            $env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$backendPort"
            $needBuild = -not ($repoReady -and $depsReady -and (Test-Path $nextDir))
            if ($backendPort -ne $script:DEFAULT_BACKEND_PORT) {
                $needBuild = $true
                Write-Host "Backend port changed, rebuilding frontend to update API URL."
            }
            if ($needBuild) {
                pnpm build
            } else {
                Write-Host "Next.js build is up to date. Skipping build step."
            }
            $env:PORT = $frontendPort
            pnpm start
        } else {
            $env:WINDOW_MODE = $Variant
            $env:PORT = $frontendPort
            $env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$backendPort"
            pnpm dev
        }
    } finally {
        if ($agentosJob -and $agentosJob.State -eq "Running") {
            Stop-Job $agentosJob | Out-Null
        }
        if ($agentosJob) {
            Remove-Job $agentosJob -Force | Out-Null
        }
        if ($backendJob -and $backendJob.State -eq "Running") {
            Stop-Job $backendJob | Out-Null
        }
        if ($backendJob) {
            Remove-Job $backendJob -Force | Out-Null
        }
    }
} elseif ($Mode -eq "tauri") {
    Set-Location (Join-Path (Get-Location).Path "free-todo-frontend")
    if (-not $frontendModulesReady) {
        pnpm install
    }

    if ($Frontend -eq "build") {
        $artifact = Find-TauriArtifact -FrontendDir (Get-Location).Path -Variant $Variant -Backend $Backend
        if (-not ($repoReady -and $depsReady -and $artifact)) {
            pnpm "build:tauri:${Variant}:${Backend}:full"
            $artifact = Find-TauriArtifact -FrontendDir (Get-Location).Path -Variant $Variant -Backend $Backend
        } else {
            Write-Host "Tauri build is up to date. Skipping build step."
        }
        if (-not (Start-BuiltApp $artifact)) {
            Write-Host "Build complete. Open the artifact under src-tauri\\target\\release\\bundle."
        }
    } else {
        $uvPath = (Get-Command uv).Source
        $backendJob = Start-Job -ScriptBlock {
            param($RepoDir, $UvPath, $PythonCmd, $BackendPort)
            Set-Location $RepoDir
            & $UvPath run $PythonCmd -m lifetrace.server --port $BackendPort
        } -ArgumentList (Resolve-Path "..").Path, $uvPath, $pythonCmd, $backendPort

        $agentosJob = Start-Job -ScriptBlock {
            param($RepoDir, $UvPath, $PythonCmd, $AgentosPort)
            Set-Location $RepoDir
            $env:LIFETRACE__AGNO__AGENT_OS__PORT = $AgentosPort
            & $UvPath run $PythonCmd -m lifetrace.agent_os
        } -ArgumentList (Resolve-Path "..").Path, $uvPath, $pythonCmd, $agentosPort

        $frontendJob = Start-Job -ScriptBlock {
            param($FrontendDir, $Variant, $FrontendPort, $BackendPort)
            Set-Location $FrontendDir
            $env:WINDOW_MODE = $Variant
            $env:PORT = $FrontendPort
            $env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$BackendPort"
            pnpm dev
        } -ArgumentList (Get-Location).Path, $Variant, $frontendPort, $backendPort

        try {
            pnpm tauri:dev
        } finally {
            if ($agentosJob -and $agentosJob.State -eq "Running") {
                Stop-Job $agentosJob | Out-Null
            }
            if ($agentosJob) {
                Remove-Job $agentosJob -Force | Out-Null
            }
            if ($frontendJob -and $frontendJob.State -eq "Running") {
                Stop-Job $frontendJob | Out-Null
            }
            if ($frontendJob) {
                Remove-Job $frontendJob -Force | Out-Null
            }
            if ($backendJob -and $backendJob.State -eq "Running") {
                Stop-Job $backendJob | Out-Null
            }
            if ($backendJob) {
                Remove-Job $backendJob -Force | Out-Null
            }
        }
    }
} else {
    Set-Location (Join-Path (Get-Location).Path "free-todo-frontend")
    if (-not $frontendModulesReady) {
        pnpm install
    }

    if ($Frontend -eq "build") {
        $artifact = Find-ElectronArtifact -FrontendDir (Get-Location).Path -Variant $Variant -Backend $Backend
        if (-not ($repoReady -and $depsReady -and $artifact)) {
            pnpm "build:electron:${Variant}:${Backend}:full:dir"
            $artifact = Find-ElectronArtifact -FrontendDir (Get-Location).Path -Variant $Variant -Backend $Backend
        } else {
            Write-Host "Electron build is up to date. Skipping build step."
        }
        if (-not (Start-BuiltApp $artifact)) {
            Write-Host "Build complete. Open the artifact under dist-artifacts\\electron."
        }
    } else {
        if ($Backend -eq "pyinstaller") {
            throw "backend=pyinstaller is only supported with frontend=build."
        }
        $uvPath = (Get-Command uv).Source
        $repoDir = (Resolve-Path "..").Path
        $agentosJob = Start-Job -ScriptBlock {
            param($RepoDir, $UvPath, $PythonCmd, $AgentosPort)
            Set-Location $RepoDir
            $env:LIFETRACE__AGNO__AGENT_OS__PORT = $AgentosPort
            & $UvPath run $PythonCmd -m lifetrace.agent_os
        } -ArgumentList $repoDir, $uvPath, $pythonCmd, $agentosPort

        try {
            $env:PORT = $frontendPort
            $env:BACKEND_PORT = $backendPort
            $env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$backendPort"
            if ($Variant -eq "island") {
                pnpm electron:dev:island
            } else {
                pnpm electron:dev
            }
        } finally {
            if ($agentosJob -and $agentosJob.State -eq "Running") {
                Stop-Job $agentosJob | Out-Null
            }
            if ($agentosJob) {
                Remove-Job $agentosJob -Force | Out-Null
            }
        }
    }
}
