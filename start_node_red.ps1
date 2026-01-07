# Start Node-RED for ICT Airport Email Reports
# Quick Start Script

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   Starting Node-RED Email Report System" -ForegroundColor Green
Write-Host "   ICT Airport Operations Intelligence Platform" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Starting Node-RED..." -ForegroundColor Cyan
Write-Host "Please wait..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Once Node-RED starts:" -ForegroundColor Cyan
Write-Host "1. Open your browser to: http://127.0.0.1:1880" -ForegroundColor White
Write-Host "2. Configure your email settings (see NODE_RED_SETUP_GUIDE.md)" -ForegroundColor White
Write-Host "3. Click the 'Deploy' button (top-right)" -ForegroundColor White
Write-Host "4. Test reports by clicking the timer node buttons" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop Node-RED" -ForegroundColor Yellow
Write-Host ""
Write-Host "------------------------------------------------------------------" -ForegroundColor Gray

# Start Node-RED
node-red
