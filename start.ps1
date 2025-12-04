# Start Airport Flight Tracker - One-Command Launcher
# Usage: powershell -ExecutionPolicy Bypass -File .\start.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Airport Flight Tracker - Starting..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Find Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
$pythonCmd = "py"
$version = & py -3 --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Found $version" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+." -ForegroundColor Red
    exit 1
}

# Install requirements
Write-Host "[2/4] Installing requirements (one-time)..." -ForegroundColor Yellow
& $pythonCmd -3 -m pip install -q -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Download logo
Write-Host "[3/4] Ensuring brand logo is ready..." -ForegroundColor Yellow
if (Test-Path "static\logo.png") {
    Write-Host "[OK] Logo already downloaded" -ForegroundColor Green
} else {
    Write-Host "  Downloading logo..." -ForegroundColor Gray
    & $pythonCmd -3 download_logo.py 2>&1 | Out-Null
    if (Test-Path "static\logo.png") {
        Write-Host "[OK] Logo downloaded" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Could not download logo (continuing anyway)" -ForegroundColor Yellow
    }
}

# Start server and open browser
Write-Host "[4/4] Starting production server..." -ForegroundColor Yellow
Write-Host "  Server: http://127.0.0.1:5001" -ForegroundColor Gray
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "" -ForegroundColor Gray

# Open browser in background after a brief delay
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5001/" -ErrorAction SilentlyContinue

# Run the server (foreground, so Ctrl+C works easily)
& $pythonCmd -3 serve_prod.py
