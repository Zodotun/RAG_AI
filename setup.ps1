# One-time setup for RAG_AI on a Windows PC. Safe to re-run; anything already installed is skipped.
# Run from the repo folder:
#   powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$LLM_MODEL   = 'llama3.2:3b'
$EMBED_MODEL = 'nomic-embed-text'

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Winget-Install($id, $extraArgs) {
    Write-Host "Installing $id ..." -ForegroundColor Cyan
    winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements --silent @extraArgs
    if ($LASTEXITCODE -ne 0) { throw "winget failed to install $id (exit code $LASTEXITCODE)" }
    Refresh-Path
}

function Find-Python {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Program Files\Python312\python.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    # Microsoft Store and other installs are only reachable through the py launcher.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $ErrorActionPreference = 'Continue'
        $exe = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    return $null
}

function Find-Ollama {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $default = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $default) { return $default }
    return $null
}

function Test-OllamaServer {
    # `ollama list` exits non-zero when the server isn't reachable. (An HTTP probe of
    # localhost can stall on IPv6/proxy lookup in Windows PowerShell, so avoid that.)
    $ErrorActionPreference = 'Continue'
    & $ollama list *> $null
    return ($LASTEXITCODE -eq 0)
}

# --- Git ---------------------------------------------------------------------
Refresh-Path
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Winget-Install 'Git.Git' @() }
else { Write-Host 'Git already installed.' -ForegroundColor Green }

# --- Python 3.12 -------------------------------------------------------------
$python = Find-Python
if (-not $python) {
    Winget-Install 'Python.Python.3.12' @('--scope', 'user')
    $python = Find-Python
    if (-not $python) { throw 'Python 3.12 installed but python.exe was not found.' }
}
else { Write-Host "Python already installed: $python" -ForegroundColor Green }

# --- Ollama ------------------------------------------------------------------
$ollama = Find-Ollama
if (-not $ollama) {
    Winget-Install 'Ollama.Ollama' @()
    $ollama = Find-Ollama
    if (-not $ollama) { throw 'Ollama installed but ollama.exe was not found.' }
}
else { Write-Host "Ollama already installed: $ollama" -ForegroundColor Green }

if (-not (Test-OllamaServer)) {
    Write-Host 'Starting Ollama server ...' -ForegroundColor Cyan
    Start-Process $ollama -ArgumentList 'serve' -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Test-OllamaServer)) {
        if ((Get-Date) -gt $deadline) { throw 'Ollama server did not start within 60 seconds.' }
        Start-Sleep -Seconds 2
    }
}

foreach ($model in @($LLM_MODEL, $EMBED_MODEL)) {
    Write-Host "Pulling model $model ..." -ForegroundColor Cyan
    & $ollama pull $model
    if ($LASTEXITCODE -ne 0) { throw "ollama pull $model failed (exit code $LASTEXITCODE)" }
}

# --- Python virtual environment + packages -----------------------------------
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Creating virtual environment .venv ...' -ForegroundColor Cyan
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create .venv' }
}

$venvPython = Resolve-Path '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'pip install -r requirements.txt failed' }

Write-Host ''
Write-Host 'Setup complete.' -ForegroundColor Green
Write-Host 'Activate the environment with:  .\.venv\Scripts\Activate.ps1'
