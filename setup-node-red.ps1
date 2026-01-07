# Node-RED Configuration and Setup
# ICT Airport Operations Intelligence Platform

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   Node-RED Complete Setup & Configuration" -ForegroundColor Green
Write-Host "   ICT Airport Operations Intelligence Platform" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

# Configuration
$SMTP_SERVER = "smtp.gmail.com"
$SMTP_PORT = 587
$NODE_RED_PORT = 1880
$API_BASE = "http://127.0.0.1:5001"
$PROJECT_PATH = "$PSScriptRoot"

Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  SMTP Server: $SMTP_SERVER" -ForegroundColor White
Write-Host "  SMTP Port: $SMTP_PORT" -ForegroundColor White
Write-Host "  Node-RED Port: $NODE_RED_PORT" -ForegroundColor White
Write-Host "  API Base: $API_BASE" -ForegroundColor White
Write-Host ""

# Step 1: Check prerequisites
Write-Host "Step 1: Checking Prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Check Node.js
Write-Host "  Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "  ✓ Node.js installed: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node.js is not installed!" -ForegroundColor Red
    Write-Host "    Download from: https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "    Press Enter to exit"
    exit 1
}

# Check npm
Write-Host "  Checking npm..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version
    Write-Host "  ✓ npm installed: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ npm is not installed!" -ForegroundColor Red
    exit 1
}

# Check Node-RED
Write-Host "  Checking Node-RED..." -ForegroundColor Yellow
try {
    $nodeRedVersion = node-red --version 2>&1
    Write-Host "  ✓ Node-RED installed: $nodeRedVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node-RED not found, installing..." -ForegroundColor Yellow
    npm install -g node-red
    Write-Host "  ✓ Node-RED installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Installing Required Node-RED Packages..." -ForegroundColor Cyan
Write-Host ""

$packages = @(
    "node-red-contrib-cronplus",
    "node-red-node-email",
    "node-red-contrib-http-request"
)

foreach ($package in $packages) {
    Write-Host "  Installing $package..." -ForegroundColor Yellow
    npm install -g $package
    Write-Host "  ✓ $package installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 3: Creating Node-RED Configuration..." -ForegroundColor Cyan
Write-Host ""

# Create or check .node-red directory
$nodeRedDir = Join-Path $env:USERPROFILE ".node-red"
if (-not (Test-Path $nodeRedDir)) {
    New-Item -ItemType Directory -Path $nodeRedDir -Force | Out-Null
    Write-Host "  ✓ Created Node-RED config directory" -ForegroundColor Green
}

# Copy flows.json to Node-RED directory
$flowsSource = Join-Path $PROJECT_PATH "node-red-flows.json"
$flowsTarget = Join-Path $nodeRedDir "flows.json"

if (Test-Path $flowsSource) {
    Copy-Item $flowsSource $flowsTarget -Force
    Write-Host "  ✓ Flows file installed to: $flowsTarget" -ForegroundColor Green
} else {
    Write-Host "  ⚠ flows.json not found at $flowsSource" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 4: Email Configuration Instructions..." -ForegroundColor Cyan
Write-Host ""
Write-Host "For Gmail (Recommended - Free):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Enable 2-Factor Authentication:" -ForegroundColor White
Write-Host "     https://myaccount.google.com/security" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Generate App Password:" -ForegroundColor White
Write-Host "     https://myaccount.google.com/apppasswords" -ForegroundColor Cyan
Write-Host "     Select: Mail > Windows Computer > Generate" -ForegroundColor White
Write-Host ""
Write-Host "  3. Configure Environment Variables:" -ForegroundColor White
Write-Host "     SMTP_SERVER=smtp.gmail.com" -ForegroundColor White
Write-Host "     SMTP_PORT=587" -ForegroundColor White
Write-Host "     SMTP_USER=your-email@gmail.com" -ForegroundColor White
Write-Host "     SMTP_PASS=<16-char app password>" -ForegroundColor White
Write-Host "     EMAIL_TO=recipient@gmail.com" -ForegroundColor White
Write-Host ""

Write-Host "For Outlook/Hotmail:" -ForegroundColor Yellow
Write-Host "     SMTP_SERVER=smtp-mail.outlook.com" -ForegroundColor White
Write-Host "     SMTP_PORT=587" -ForegroundColor White
Write-Host "     SMTP_USER=your-email@outlook.com" -ForegroundColor White
Write-Host "     SMTP_PASS=your-password" -ForegroundColor White
Write-Host ""

# Create .env file for Node-RED if it doesn't exist
$envFile = Join-Path $PROJECT_PATH ".env.node-red"
if (-not (Test-Path $envFile)) {
    $envContent = @"
# Node-RED Email Configuration
# Update these values with your email provider settings

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_TO=recipient@gmail.com
NODE_RED_PORT=1880
API_BASE=http://127.0.0.1:5001
"@
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "  ✓ Created .env.node-red template (update with your credentials)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 5: Starting Node-RED..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Starting Node-RED on port $NODE_RED_PORT..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Once started, open your browser to:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:$NODE_RED_PORT" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then configure the email nodes:" -ForegroundColor Yellow
Write-Host "  1. Find the 'Send Email' nodes (2 total)" -ForegroundColor White
Write-Host "  2. Click the pencil icon to add email configuration" -ForegroundColor White
Write-Host "  3. Enter SMTP settings from above" -ForegroundColor White
Write-Host "  4. Click 'Deploy' to save flows" -ForegroundColor White
Write-Host ""
Write-Host "Test Reports:" -ForegroundColor Yellow
Write-Host "  1. Click the button on 'Manual Daily (Test)' node to test daily report" -ForegroundColor White
Write-Host "  2. Click the button on 'Manual Weekly (Test)' node to test weekly report" -ForegroundColor White
Write-Host "  3. Check your email for the formatted reports" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop Node-RED" -ForegroundColor Yellow
Write-Host ""
Write-Host "------------------------------------------------------------------" -ForegroundColor Gray

# Start Node-RED with environment variables
$env:SMTP_SERVER = $SMTP_SERVER
$env:SMTP_PORT = $SMTP_PORT
$env:NODE_RED_PORT = $NODE_RED_PORT

# Load .env if it exists
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*[^#]' -and $_ -match '=') {
            $parts = $_ -split '=', 2
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                Set-Item -Path "env:$key" -Value $value
            }
        }
    }
}

node-red

