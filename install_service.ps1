# ICT Flight Tracker - Service Installation Script
# Installs the flight tracker as a Windows Service

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ICT Flight Tracker - Service Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script requires Administrator privileges" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Installation Directory: $scriptDir" -ForegroundColor White
Write-Host ""

# Step 1: Install required Python packages
Write-Host "[1/6] Installing required Python packages..." -ForegroundColor Yellow

$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python virtual environment not found" -ForegroundColor Red
    Write-Host "Expected: $pythonExe" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Install service-specific packages
& $pythonExe -m pip install pywin32 schedule psutil --quiet --disable-pip-version-check

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install required packages" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  Packages installed successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Create logs directory
Write-Host "[2/6] Creating logs directory..." -ForegroundColor Yellow

$logsDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

Write-Host "  Logs directory ready: $logsDir" -ForegroundColor Green
Write-Host ""

# Step 3: Create backups directory
Write-Host "[3/6] Creating backups directory..." -ForegroundColor Yellow

$backupsDir = Join-Path $scriptDir "backups"
if (-not (Test-Path $backupsDir)) {
    New-Item -ItemType Directory -Path $backupsDir | Out-Null
}

$archiveDir = Join-Path $backupsDir "archive"
if (-not (Test-Path $archiveDir)) {
    New-Item -ItemType Directory -Path $archiveDir | Out-Null
}

Write-Host "  Backup directories ready" -ForegroundColor Green
Write-Host ""

# Step 4: Stop existing service if running
Write-Host "[4/6] Checking for existing service..." -ForegroundColor Yellow

$serviceName = "ICTFlightTracker"
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if ($existingService) {
    Write-Host "  Existing service found - stopping..." -ForegroundColor Yellow
    
    if ($existingService.Status -eq 'Running') {
        Stop-Service -Name $serviceName -Force
        Start-Sleep -Seconds 3
    }
    
    Write-Host "  Removing old service..." -ForegroundColor Yellow
    & $pythonExe (Join-Path $scriptDir "service_wrapper.py") remove
    Start-Sleep -Seconds 2
}

Write-Host "  Ready for installation" -ForegroundColor Green
Write-Host ""

# Step 5: Install the Windows Service
Write-Host "[5/6] Installing Windows Service..." -ForegroundColor Yellow

& $pythonExe (Join-Path $scriptDir "service_wrapper.py") install

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install service" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  Service installed successfully" -ForegroundColor Green
Write-Host ""

# Step 6: Start the service
Write-Host "[6/6] Starting service..." -ForegroundColor Yellow

Start-Service -Name $serviceName

# Wait a moment and check status
Start-Sleep -Seconds 3
$service = Get-Service -Name $serviceName

if ($service.Status -eq 'Running') {
    Write-Host "  Service started successfully!" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Service installed but not running" -ForegroundColor Yellow
    Write-Host "  Status: $($service.Status)" -ForegroundColor Yellow
    Write-Host "  Check logs in: $logsDir" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service Details:" -ForegroundColor White
Write-Host "  Name:        $serviceName" -ForegroundColor White
Write-Host "  Display:     ICT Flight Tracker Dashboard" -ForegroundColor White
Write-Host "  Status:      $($service.Status)" -ForegroundColor White
Write-Host "  Start Type:  $($service.StartType)" -ForegroundColor White
Write-Host ""
Write-Host "Dashboard URL:" -ForegroundColor White
Write-Host "  http://127.0.0.1:5001/static/index.html" -ForegroundColor Cyan
Write-Host ""
Write-Host "Log Files:" -ForegroundColor White
Write-Host "  Service:     $logsDir\service.log" -ForegroundColor White
Write-Host "  Application: $logsDir\application.log" -ForegroundColor White
Write-Host "  Errors:      $logsDir\errors.log" -ForegroundColor White
Write-Host "  Health:      $logsDir\health.log" -ForegroundColor White
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor White
Write-Host "  View Status:   Get-Service ICTFlightTracker | Format-List *" -ForegroundColor Gray
Write-Host "  Stop Service:  Stop-Service ICTFlightTracker" -ForegroundColor Gray
Write-Host "  Start Service: Start-Service ICTFlightTracker" -ForegroundColor Gray
Write-Host "  View Logs:     Get-Content logs\service.log -Tail 50 -Wait" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open http://127.0.0.1:5001/static/index.html in your browser" -ForegroundColor White
Write-Host "  2. Run .\setup_tasks.ps1 to configure backup and monitoring tasks" -ForegroundColor White
Write-Host "  3. Check service logs to verify operation" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
