## start_background.ps1
# Starts the included `run_server.ps1` in the background (hidden window).
# Writes a short status message to the console. Logs are left in the project folder.

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$fullTarget = Join-Path $root 'run_server.ps1'

if (-not (Test-Path $fullTarget)) {
    Write-Error "run_server.ps1 not found in $root"
    exit 1
}

Write-Host "Starting Airport Tracker in background (hidden window)..."
# Launch `run_server.ps1` using PowerShell in a hidden window.
# Logging/rotation is handled inside the Python process via RotatingFileHandler.
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$fullTarget`""
Start-Process -FilePath 'powershell.exe' -ArgumentList $arg -WorkingDirectory $root -WindowStyle Hidden

Write-Host "Launched hidden background starter. Python now handles logging/rotation (server.log)"
