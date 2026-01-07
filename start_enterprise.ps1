# Enterprise Flight Tracker - Production Deployment
# Run with: .\start_enterprise.ps1

Write-Host "`n=== ENTERPRISE FLIGHT TRACKER DEPLOYMENT ===" -ForegroundColor Green
Write-Host "Starting production-grade server...`n" -ForegroundColor Cyan

# Check if virtual environment exists
if (!(Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing enterprise dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet --upgrade

# Create logs directory
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Check if Redis is running
Write-Host "Checking Redis server..." -ForegroundColor Yellow
$redisRunning = Get-Process redis-server -ErrorAction SilentlyContinue
if (!$redisRunning) {
    Write-Host "  Starting Redis server..." -ForegroundColor Cyan
    Start-Process -FilePath "redis\redis-server.exe" -ArgumentList "redis\redis.conf" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# Set environment variables
$env:ENVIRONMENT = "production"
$env:LOG_LEVEL = "INFO"
$env:LOG_FORMAT = "json"

Write-Host "`n=== STARTING ENTERPRISE SERVER ===" -ForegroundColor Green
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  - Environment: Production" -ForegroundColor White
Write-Host "  - Server: Waitress (Production WSGI)" -ForegroundColor White
Write-Host "  - Host: 0.0.0.0" -ForegroundColor White
Write-Host "  - Port: 5001" -ForegroundColor White
Write-Host "  - Workers: 4" -ForegroundColor White
Write-Host "  - Rate Limiting: Enabled" -ForegroundColor White
Write-Host "  - Metrics: Enabled (port 9090)" -ForegroundColor White
Write-Host "  - Structured Logging: JSON" -ForegroundColor White
Write-Host "  - Security Headers: Enabled" -ForegroundColor White
Write-Host "  - CORS: Configured" -ForegroundColor White
Write-Host "  - Circuit Breaker: Enabled" -ForegroundColor White
Write-Host "`nAPI Authentication Required:" -ForegroundColor Yellow
Write-Host "  Include header: X-API-Key: enterprise-key-2025`n" -ForegroundColor White

Write-Host "Starting server..." -ForegroundColor Green
Write-Host "Dashboard URL: http://localhost:5001" -ForegroundColor Cyan
Write-Host "Metrics URL: http://localhost:5001/metrics" -ForegroundColor Cyan
Write-Host "Health Check: http://localhost:5001/health" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop the server`n" -ForegroundColor Yellow

# Start the enterprise server
python api_enterprise.py
