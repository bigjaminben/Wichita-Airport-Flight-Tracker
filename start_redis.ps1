# Start Redis Server for Flight Tracker
# Starts Redis in background for real-time caching

Write-Host "Starting Redis server..." -ForegroundColor Cyan

$redisExe = Join-Path $PSScriptRoot "redis\redis-server.exe"

if (-not (Test-Path $redisExe)) {
    Write-Host "Error: Redis not found at $redisExe" -ForegroundColor Red
    Write-Host "Please run the Redis installation first." -ForegroundColor Yellow
    exit 1
}

# Check if Redis is already running
$redisProcess = Get-Process redis-server -ErrorAction SilentlyContinue
if ($redisProcess) {
    Write-Host "Redis is already running (PID: $($redisProcess.Id))" -ForegroundColor Yellow
    exit 0
}

# Start Redis server in hidden window
$redisConf = Join-Path $PSScriptRoot "redis\redis.windows.conf"
Start-Process -FilePath $redisExe -ArgumentList $redisConf -WindowStyle Hidden

Start-Sleep -Seconds 2

# Verify Redis started
$redisProcess = Get-Process redis-server -ErrorAction SilentlyContinue
if ($redisProcess) {
    Write-Host "Redis server started successfully (PID: $($redisProcess.Id))" -ForegroundColor Green
    Write-Host "  Port: 6379" -ForegroundColor Green
    Write-Host "  Real-time caching: ACTIVE" -ForegroundColor Green
} else {
    Write-Host "Failed to start Redis server" -ForegroundColor Red
    exit 1
}
