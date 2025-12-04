param(
    [string]$TaskName = "AirportTracker",
    [string]$Trigger = "ONLOGON"
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
# Schedule the background starter so the server runs hidden and logs are captured
$fullTarget = Join-Path $root 'start_background.ps1'

if (-not (Test-Path $fullTarget)) {
    Write-Error "run_server.ps1 not found in $root: $fullTarget"
    exit 1
}

$action = '"powershell.exe" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $fullTarget + '"'

Write-Host "Registering scheduled task '$TaskName' to run at $Trigger..."

# Use schtasks.exe which is available on Windows to register a task for current user
schtasks /Create /SC $Trigger /TN $TaskName /TR $action /F

if ($LASTEXITCODE -eq 0) {
    Write-Host "Scheduled task '$TaskName' created. It will run at $Trigger for the current user." -ForegroundColor Green
} else {
    Write-Error "Failed to create scheduled task. Exit code: $LASTEXITCODE"
}
