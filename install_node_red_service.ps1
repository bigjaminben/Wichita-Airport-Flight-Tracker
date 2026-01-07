# Install Node-RED as Windows Service
# ICT Airport Operations Intelligence Platform - Email Report Automation

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   Node-RED Service Installation" -ForegroundColor Green
Write-Host "   ICT Airport Operations Intelligence Platform" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run this script again." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Running with Administrator privileges" -ForegroundColor Green
Write-Host ""

# Check if Node.js is installed
Write-Host "Checking Node.js installation..." -ForegroundColor Cyan
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js installed: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js is not installed!" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org and run this script again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Node-RED is installed
Write-Host "Checking Node-RED installation..." -ForegroundColor Cyan
try {
    $nodeRedVersion = node-red --version 2>&1 | Select-String "Node-RED"
    Write-Host "✓ Node-RED installed: $nodeRedVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node-RED is not installed!" -ForegroundColor Red
    Write-Host "Installing Node-RED globally..." -ForegroundColor Yellow
    npm install -g node-red
    Write-Host "✓ Node-RED installed successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "Installing node-windows (service helper)..." -ForegroundColor Cyan
npm install -g node-windows

Write-Host ""
Write-Host "Creating service installation script..." -ForegroundColor Cyan

# Create service install script
$serviceScript = @"
var Service = require('node-windows').Service;

// Create a new service object
var svc = new Service({
  name: 'NodeRED - ICT Airport Reports',
  description: 'Node-RED service for automated email reports - ICT Airport Operations Intelligence Platform',
  script: require('path').join(process.env.APPDATA, 'npm', 'node_modules', 'node-red', 'red.js'),
  nodeOptions: [
    '--max-old-space-size=256'
  ],
  env: [
    {
      name: 'PORT',
      value: '1880'
    },
    {
      name: 'NODE_ENV',
      value: 'production'
    }
  ]
});

// Listen for the install event
svc.on('install', function() {
  console.log('Node-RED service installed successfully!');
  console.log('Starting service...');
  svc.start();
});

svc.on('start', function() {
  console.log('Node-RED service started!');
  console.log('Access Node-RED at: http://127.0.0.1:1880');
});

svc.on('alreadyinstalled', function() {
  console.log('Service is already installed.');
});

// Install the service
svc.install();
"@

$tempScriptPath = Join-Path $env:TEMP "install-node-red-service.js"
$serviceScript | Out-File -FilePath $tempScriptPath -Encoding UTF8

Write-Host "✓ Service script created" -ForegroundColor Green
Write-Host ""
Write-Host "Installing Node-RED as Windows Service..." -ForegroundColor Cyan
Write-Host "This may take a minute..." -ForegroundColor Yellow
Write-Host ""

# Run the service installer
node $tempScriptPath

Write-Host ""
Write-Host "Waiting for service to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Check if service is running
$service = Get-Service -Name "*NodeRED*" -ErrorAction SilentlyContinue

if ($service) {
    Write-Host "✓ Service installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service Name: $($service.Name)" -ForegroundColor White
    Write-Host "Status: $($service.Status)" -ForegroundColor $(if ($service.Status -eq 'Running') { 'Green' } else { 'Yellow' })
    Write-Host "Startup Type: $($service.StartType)" -ForegroundColor White
    Write-Host ""
    
    if ($service.Status -ne 'Running') {
        Write-Host "Starting service..." -ForegroundColor Cyan
        Start-Service $service.Name
        Start-Sleep -Seconds 3
        $service = Get-Service -Name $service.Name
        Write-Host "✓ Service started: $($service.Status)" -ForegroundColor Green
    }
} else {
    Write-Host "⚠ Could not find installed service" -ForegroundColor Yellow
    Write-Host "Check if the service was installed manually" -ForegroundColor Yellow
}

# Clean up temp script
Remove-Item $tempScriptPath -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Open your browser to: http://127.0.0.1:1880" -ForegroundColor White
Write-Host "2. Configure email credentials in the email nodes" -ForegroundColor White
Write-Host "3. Click 'Deploy' to activate the flows" -ForegroundColor White
Write-Host "4. Test by clicking the button on the timer nodes" -ForegroundColor White
Write-Host ""
Write-Host "See NODE_RED_SETUP_GUIDE.md for detailed instructions" -ForegroundColor Yellow
Write-Host ""
Write-Host "Service Management Commands:" -ForegroundColor Cyan
Write-Host "  Start:   net start 'NodeRED - ICT Airport Reports'" -ForegroundColor White
Write-Host "  Stop:    net stop 'NodeRED - ICT Airport Reports'" -ForegroundColor White
Write-Host "  Status:  Get-Service '*NodeRED*'" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
