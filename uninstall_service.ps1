# ICT Flight Tracker - Service Uninstaller
# Removes the Windows Service

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ICT Flight Tracker - Service Uninstaller" -ForegroundColor Cyan
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

$serviceName = "ICTFlightTracker"
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"

# Check if service exists
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if (-not $service) {
    Write-Host "Service '$serviceName' is not installed" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 0
}

Write-Host "Current Status: $($service.Status)" -ForegroundColor White
Write-Host ""

# Confirm uninstallation
$confirm = Read-Host "Are you sure you want to uninstall the service? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Uninstallation cancelled" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 0
}

Write-Host ""

# Step 1: Stop the service
Write-Host "[1/2] Stopping service..." -ForegroundColor Yellow

if ($service.Status -eq 'Running') {
    Stop-Service -Name $serviceName -Force
    Start-Sleep -Seconds 3
    Write-Host "  Service stopped" -ForegroundColor Green
} else {
    Write-Host "  Service already stopped" -ForegroundColor Gray
}

Write-Host ""

# Step 2: Remove the service
Write-Host "[2/2] Removing service..." -ForegroundColor Yellow

& $pythonExe (Join-Path $scriptDir "service_wrapper.py") remove

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to remove service" -ForegroundColor Red
    Write-Host "You may need to remove it manually using sc.exe:" -ForegroundColor Yellow
    Write-Host "  sc delete $serviceName" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  Service removed successfully" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Uninstallation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Notes:" -ForegroundColor White
Write-Host "  - Service has been removed from Windows Services" -ForegroundColor White
Write-Host "  - Application files remain in: $scriptDir" -ForegroundColor White
Write-Host "  - Database and logs are preserved" -ForegroundColor White
Write-Host ""
Write-Host "To run manually, use: .\start.ps1" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"
