# Start Flight Tracker + Node-RED Complete System
# ICT Airport Operations Intelligence Platform

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   ICT Airport Flight Tracker + Node-RED Email System" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

$projectPath = $PSScriptRoot

# Step 1: Check Flask API
Write-Host "Step 1: Starting Flask API Server..." -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = py -3 --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python 3 not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Start Flask API in background
Write-Host "Starting Flask API on http://127.0.0.1:5001..." -ForegroundColor Yellow
$flaskProcess = Start-Process -FilePath "py" -ArgumentList "-3", "serve_prod.py" -WorkingDirectory $projectPath -PassThru -NoNewWindow
Write-Host "✓ Flask API started (PID: $($flaskProcess.Id))" -ForegroundColor Green

Start-Sleep -Seconds 2

# Verify Flask is responding
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:5001/api/flights" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host "✓ Flask API is responding" -ForegroundColor Green
} catch {
    Write-Host "⚠ Flask API not responding yet (may still be starting)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 2: Starting Node-RED Email System..." -ForegroundColor Cyan
Write-Host ""

# Check Node-RED
try {
    $nodeRedVersion = node-red --version 2>&1
    Write-Host "✓ Node-RED found: $nodeRedVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node-RED not installed!" -ForegroundColor Red
    Write-Host "Run: npm install -g node-red" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Continuing without Node-RED (email reports disabled)" -ForegroundColor Yellow
    Write-Host ""
}

# Ask if user wants to start Node-RED
Write-Host "Start Node-RED for email reports?" -ForegroundColor Yellow
$startNodeRed = Read-Host "(Y/N, default: Y)"

if ($startNodeRed -eq "N" -or $startNodeRed -eq "n") {
    Write-Host ""
    Write-Host "Skipping Node-RED" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Starting Node-RED on http://127.0.0.1:1880..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Node-RED will start in a new window" -ForegroundColor Cyan
    Write-Host "Please wait..." -ForegroundColor Yellow
    
    # Start Node-RED in a new window
    Start-Process -FilePath "node-red" -WorkingDirectory $projectPath -NoNewWindow
    
    Start-Sleep -Seconds 3
    Write-Host "✓ Node-RED starting..." -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   System Ready!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services Started:" -ForegroundColor Cyan
Write-Host "  ✓ Flask API Server" -ForegroundColor Green
Write-Host "    URL: http://127.0.0.1:5001" -ForegroundColor White
Write-Host "    PID: $($flaskProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "  ✓ Node-RED Email Automation (if started)" -ForegroundColor Green
Write-Host "    URL: http://127.0.0.1:1880" -ForegroundColor White
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open dashboard: http://127.0.0.1:5001" -ForegroundColor White
Write-Host "  2. View live flights and weather" -ForegroundColor White
Write-Host "  3. Configure Node-RED at http://127.0.0.1:1880 (if running)" -ForegroundColor White
Write-Host "  4. Set email credentials for automated reports" -ForegroundColor White
Write-Host ""

Write-Host "Stop Services:" -ForegroundColor Yellow
Write-Host "  To stop Flask:     Kill process $($flaskProcess.Id) or press Ctrl+C in Flask window" -ForegroundColor White
Write-Host "  To stop Node-RED:  Close the Node-RED window or press Ctrl+C" -ForegroundColor White
Write-Host ""

Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  Flask API:  README.md" -ForegroundColor White
Write-Host "  Node-RED:   NODE_RED_COMPLETE_GUIDE.md" -ForegroundColor White
Write-Host ""

Write-Host "------------------------------------------------------------------" -ForegroundColor Gray
Write-Host "System running. Press Ctrl+C to exit." -ForegroundColor Cyan
Write-Host "------------------------------------------------------------------" -ForegroundColor Gray
Write-Host ""

# Wait for processes
while ($true) {
    # Check if Flask process is still running
    $flaskRunning = Get-Process -Id $flaskProcess.Id -ErrorAction SilentlyContinue
    
    if (-not $flaskRunning) {
        Write-Host ""
        Write-Host "Flask API process has stopped" -ForegroundColor Red
        break
    }
    
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "System shutdown." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
