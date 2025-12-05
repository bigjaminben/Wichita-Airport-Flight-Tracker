# ICT Flight Tracker - Setup Automated Tasks
# Configures backup and health monitoring scheduled tasks

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ICT Flight Tracker - Task Setup" -ForegroundColor Cyan
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

$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"

Write-Host "Setting up automated tasks for:" -ForegroundColor White
Write-Host "  - Database backups (hourly, daily, weekly)" -ForegroundColor White
Write-Host "  - Health monitoring (every 5 minutes)" -ForegroundColor White
Write-Host ""

# Task 1: Backup Manager
Write-Host "[1/2] Creating Backup Manager task..." -ForegroundColor Yellow

$backupTaskName = "ICT Flight Tracker - Backup Manager"

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $backupTaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "  Removing existing task..." -ForegroundColor Gray
    Unregister-ScheduledTask -TaskName $backupTaskName -Confirm:$false
}

# Create action
$backupAction = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument (Join-Path $scriptDir "backup_manager.py") `
    -WorkingDirectory $scriptDir

# Create trigger (run at startup and keep running)
$backupTrigger = New-ScheduledTaskTrigger -AtStartup

# Create principal (run as SYSTEM)
$backupPrincipal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Create settings
$backupSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Register task
Register-ScheduledTask `
    -TaskName $backupTaskName `
    -Action $backupAction `
    -Trigger $backupTrigger `
    -Principal $backupPrincipal `
    -Settings $backupSettings `
    -Description "Automated backup management for ICT Flight Tracker database" | Out-Null

Write-Host "  Backup Manager task created" -ForegroundColor Green

# Start the task
Start-ScheduledTask -TaskName $backupTaskName
Write-Host "  Backup Manager started" -ForegroundColor Green
Write-Host ""

# Task 2: Health Monitor
Write-Host "[2/2] Creating Health Monitor task..." -ForegroundColor Yellow

$monitorTaskName = "ICT Flight Tracker - Health Monitor"

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $monitorTaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "  Removing existing task..." -ForegroundColor Gray
    Unregister-ScheduledTask -TaskName $monitorTaskName -Confirm:$false
}

# Create action
$monitorAction = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument (Join-Path $scriptDir "health_monitor.py") `
    -WorkingDirectory $scriptDir

# Create trigger (run at startup and keep running)
$monitorTrigger = New-ScheduledTaskTrigger -AtStartup

# Create principal (run as SYSTEM)
$monitorPrincipal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Create settings
$monitorSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Register task
Register-ScheduledTask `
    -TaskName $monitorTaskName `
    -Action $monitorAction `
    -Trigger $monitorTrigger `
    -Principal $monitorPrincipal `
    -Settings $monitorSettings `
    -Description "Health monitoring for ICT Flight Tracker service" | Out-Null

Write-Host "  Health Monitor task created" -ForegroundColor Green

# Start the task
Start-ScheduledTask -TaskName $monitorTaskName
Write-Host "  Health Monitor started" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Task Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Scheduled Tasks Created:" -ForegroundColor White
Write-Host "  1. $backupTaskName" -ForegroundColor White
Write-Host "  2. $monitorTaskName" -ForegroundColor White
Write-Host ""
Write-Host "These tasks will:" -ForegroundColor White
Write-Host "  - Start automatically when Windows boots" -ForegroundColor White
Write-Host "  - Run continuously in the background" -ForegroundColor White
Write-Host "  - Restart automatically if they fail" -ForegroundColor White
Write-Host ""
Write-Host "Backup Schedule:" -ForegroundColor White
Write-Host "  - Hourly:  Every hour" -ForegroundColor Gray
Write-Host "  - Daily:   2:00 AM" -ForegroundColor Gray
Write-Host "  - Weekly:  Sunday 3:00 AM" -ForegroundColor Gray
Write-Host "  - Archive: Sunday 6:00 AM (data older than 90 days)" -ForegroundColor Gray
Write-Host ""
Write-Host "Health Checks:" -ForegroundColor White
Write-Host "  - Every 5 minutes" -ForegroundColor Gray
Write-Host "  - Monitors API, database, system resources, backups" -ForegroundColor Gray
Write-Host "  - Logs saved to: logs\health.log" -ForegroundColor Gray
Write-Host ""
Write-Host "View Tasks:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask | Where-Object {`$_.TaskName -like 'ICT Flight*'}" -ForegroundColor Gray
Write-Host ""
Write-Host "View Task Status:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask -TaskName '$backupTaskName' | Get-ScheduledTaskInfo" -ForegroundColor Gray
Write-Host "  Get-ScheduledTask -TaskName '$monitorTaskName' | Get-ScheduledTaskInfo" -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to exit"
