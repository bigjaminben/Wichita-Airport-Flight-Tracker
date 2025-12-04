param(
    [string]$TaskName = "AirportTracker"
)

Write-Host "Removing scheduled task '$TaskName' if it exists..."
schtasks /Delete /TN $TaskName /F
if ($LASTEXITCODE -eq 0) {
    Write-Host "Scheduled task '$TaskName' removed." -ForegroundColor Green
} else {
    Write-Host "Scheduled task '$TaskName' may not exist or could not be removed (exit code: $LASTEXITCODE)." -ForegroundColor Yellow
}
