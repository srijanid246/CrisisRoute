$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvPython = Join-Path $backendDir "venv\Scripts\python.exe"

function Test-PortListening([int]$port) {
    try {
        return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

function Wait-ForPort([int]$port, [int]$timeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening $port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

if (-not (Test-Path $venvPython)) {
    Write-Host "Backend venv not found at $venvPython" -ForegroundColor Red
    Write-Host "Create it first:" -ForegroundColor Red
    Write-Host "  cd backend" -ForegroundColor Red
    Write-Host "  python -m venv venv" -ForegroundColor Red
    Write-Host "  .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "frontend\node_modules not found - running npm install..." -ForegroundColor Yellow
    Push-Location $frontendDir
    npm install
    Pop-Location
}

if (Test-PortListening 5000) {
    Write-Host "Port 5000 is already in use - assuming the backend is already running, skipping." -ForegroundColor Yellow
} else {
    Write-Host "Starting backend (Flask API) on http://localhost:5000 ..."
    Start-Process powershell -WindowStyle Normal -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$backendDir'; & '$venvPython' run_api.py"
    )
}

if (Test-PortListening 5173) {
    Write-Host "Port 5173 is already in use - assuming the frontend is already running, skipping." -ForegroundColor Yellow
} else {
    Write-Host "Starting frontend (Vite) on http://localhost:5173 ..."
    Start-Process powershell -WindowStyle Normal -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$frontendDir'; npm run dev"
    )
}

Write-Host ""
Write-Host "Waiting for both services to respond..."
$backendUp = Wait-ForPort 5000 30
$frontendUp = Wait-ForPort 5173 30

Write-Host ""
if ($backendUp) {
    Write-Host "Backend:  http://localhost:5000  [up]" -ForegroundColor Green
} else {
    Write-Host "Backend:  http://localhost:5000  [not responding yet - check its window]" -ForegroundColor Red
}
if ($frontendUp) {
    Write-Host "Frontend: http://localhost:5173  [up]" -ForegroundColor Green
} else {
    Write-Host "Frontend: http://localhost:5173  [not responding yet - check its window]" -ForegroundColor Red
}

Write-Host ""
Write-Host "Each service runs in its own window. Close a window (or Ctrl+C inside it) to stop that service."
