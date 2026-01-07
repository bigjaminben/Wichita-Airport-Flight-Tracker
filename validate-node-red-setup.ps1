# Node-RED Implementation Validation Script
# Checks all components are properly installed and configured

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   Node-RED Implementation Validation Checklist" -ForegroundColor Green
Write-Host "   ICT Airport Flight Tracker" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

$projectPath = $PSScriptRoot
$validationResults = @()
$allPassed = $true

# Function to add validation result
function Add-ValidationResult($category, $check, $passed, $details) {
    $status = if ($passed) { "✓ PASS" } else { "✗ FAIL" }
    $color = if ($passed) { "Green" } else { "Red" }
    
    Write-Host "  [$status] $category - $check" -ForegroundColor $color
    if ($details) {
        Write-Host "         $details" -ForegroundColor Gray
    }
    
    if (-not $passed) {
        $allPassed = $false
    }
}

# ============================================================================
# 1. Check Prerequisites
# ============================================================================
Write-Host ""
Write-Host "1. Checking Prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Python 3.10+
try {
    $pythonVersion = py -3 --version 2>&1
    $versionOk = $pythonVersion -match "3\.(1[0-9]|[2-9][0-9])"
    Add-ValidationResult "Python" "Version 3.10+" $versionOk "Found: $pythonVersion"
} catch {
    Add-ValidationResult "Python" "Version 3.10+" $false "Not found or not in PATH"
}

# Node.js
try {
    $nodeVersion = node --version 2>&1
    $versionOk = $nodeVersion -match "v1[4-9]\."
    Add-ValidationResult "Node.js" "Version 14+" $versionOk "Found: $nodeVersion"
} catch {
    Add-ValidationResult "Node.js" "Version 14+" $false "Not installed. Download from https://nodejs.org"
}

# npm
try {
    $npmVersion = npm --version 2>&1
    Add-ValidationResult "npm" "Installation" $true "Version: $npmVersion"
} catch {
    Add-ValidationResult "npm" "Installation" $false "Not found"
}

# ============================================================================
# 2. Check Node-RED Installation
# ============================================================================
Write-Host ""
Write-Host "2. Checking Node-RED Installation..." -ForegroundColor Cyan
Write-Host ""

# Node-RED
try {
    $nodeRedVersion = node-red --version 2>&1
    Add-ValidationResult "Node-RED" "Installation" $true "Version: $nodeRedVersion"
} catch {
    Add-ValidationResult "Node-RED" "Installation" $false "Not installed. Run: setup-node-red.ps1"
}

# Node-RED config directory
$nodeRedDir = Join-Path $env:USERPROFILE ".node-red"
$dirExists = Test-Path $nodeRedDir
Add-ValidationResult "Node-RED" "Config directory" $dirExists "Location: $nodeRedDir"

# flows.json
$flowsFile = Join-Path $nodeRedDir "flows.json"
$flowsExists = Test-Path $flowsFile
Add-ValidationResult "Node-RED" "Flows.json file" $flowsExists "Location: $flowsFile"

# ============================================================================
# 3. Check Required Packages
# ============================================================================
Write-Host ""
Write-Host "3. Checking Required Packages..." -ForegroundColor Cyan
Write-Host ""

$packages = @(
    "node-red-contrib-cronplus",
    "node-red-node-email",
    "node-red-contrib-http-request"
)

foreach ($package in $packages) {
    try {
        $result = npm list -g $package 2>&1 | Select-String $package
        $installed = $null -ne $result
        Add-ValidationResult "Packages" $package $installed ""
    } catch {
        Add-ValidationResult "Packages" $package $false ""
    }
}

# ============================================================================
# 4. Check Project Files
# ============================================================================
Write-Host ""
Write-Host "4. Checking Project Files..." -ForegroundColor Cyan
Write-Host ""

$projectFiles = @(
    ("api.py", "Flask API"),
    ("node-red-flows.json", "Node-RED flows definition"),
    ("setup-node-red.ps1", "Setup script"),
    ("start-complete-system.ps1", "Complete system launcher"),
    ("node_red_integration.py", "Flask/Node-RED integration"),
    ("NODE_RED_COMPLETE_GUIDE.md", "Complete documentation"),
    ("NODE_RED_QUICK_REFERENCE.md", "Quick reference guide"),
    ("README.md", "Main README")
)

foreach ($fileInfo in $projectFiles) {
    $file = $fileInfo[0]
    $description = $fileInfo[1]
    $path = Join-Path $projectPath $file
    $exists = Test-Path $path
    Add-ValidationResult "Files" $file $exists "Path: $path"
}

# ============================================================================
# 5. Check Python Dependencies
# ============================================================================
Write-Host ""
Write-Host "5. Checking Python Dependencies..." -ForegroundColor Cyan
Write-Host ""

$pythonDeps = @("flask", "plotly", "pandas", "numpy", "requests", "matplotlib")

foreach ($dep in $pythonDeps) {
    try {
        $result = py -3 -c "import $dep" 2>&1
        $installed = $LASTEXITCODE -eq 0
        Add-ValidationResult "Python" $dep $installed ""
    } catch {
        Add-ValidationResult "Python" $dep $false ""
    }
}

# ============================================================================
# 6. Check Services and Ports
# ============================================================================
Write-Host ""
Write-Host "6. Checking Services and Ports..." -ForegroundColor Cyan
Write-Host ""

# Flask API port
try {
    $portInUse = (netstat -ano 2>$null | Select-String ":5001" -ErrorAction SilentlyContinue) -ne $null
    if ($portInUse) {
        Add-ValidationResult "Ports" "Flask API (5001)" $true "Port is in use (Flask running)"
    } else {
        Add-ValidationResult "Ports" "Flask API (5001)" $true "Port available (Flask not running, that's OK)"
    }
} catch {
    Add-ValidationResult "Ports" "Flask API (5001)" $true "Unable to check (that's OK)"
}

# Node-RED port
try {
    $portInUse = (netstat -ano 2>$null | Select-String ":1880" -ErrorAction SilentlyContinue) -ne $null
    if ($portInUse) {
        Add-ValidationResult "Ports" "Node-RED (1880)" $true "Port is in use (Node-RED running)"
    } else {
        Add-ValidationResult "Ports" "Node-RED (1880)" $true "Port available (Node-RED not running, that's OK)"
    }
} catch {
    Add-ValidationResult "Ports" "Node-RED (1880)" $true "Unable to check (that's OK)"
}

# Check for Node-RED service
try {
    $service = Get-Service | Where-Object { $_.DisplayName -like "*node*red*" }
    if ($service) {
        Add-ValidationResult "Services" "Windows Service" $true "Service: $($service.Name) - $($service.Status)"
    } else {
        Add-ValidationResult "Services" "Windows Service" $true "Not installed (optional)"
    }
} catch {
    Add-ValidationResult "Services" "Windows Service" $true "Check skipped"
}

# ============================================================================
# 7. Check Environment Files
# ============================================================================
Write-Host ""
Write-Host "7. Checking Environment Configuration..." -ForegroundColor Cyan
Write-Host ""

# .env.node-red.example
$envExample = Join-Path $projectPath ".env.node-red.example"
$envExampleExists = Test-Path $envExample
Add-ValidationResult "Config" ".env.node-red.example" $envExampleExists "Template provided"

# .env.node-red (actual config)
$envFile = Join-Path $projectPath ".env.node-red"
$envFileExists = Test-Path $envFile
Add-ValidationResult "Config" ".env.node-red (user config)" $envFileExists "User configuration file"

if (-not $envFileExists) {
    Write-Host ""
    Write-Host "         NOTE: No .env.node-red found. To set up email:" -ForegroundColor Yellow
    Write-Host "         1. Copy .env.node-red.example to .env.node-red" -ForegroundColor Yellow
    Write-Host "         2. Edit with your email credentials" -ForegroundColor Yellow
    Write-Host "         3. See NODE_RED_COMPLETE_GUIDE.md for details" -ForegroundColor Yellow
}

# ============================================================================
# 8. API Endpoint Checks
# ============================================================================
Write-Host ""
Write-Host "8. Checking API Endpoints (if Flask is running)..." -ForegroundColor Cyan
Write-Host ""

$endpoints = @(
    "/api/flights",
    "/api/report/daily",
    "/api/report/weekly",
    "/api/node-red/health",
    "/api/node-red/report/batch"
)

$flaskRunning = $false
foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:5001$endpoint" -TimeoutSec 2 -ErrorAction SilentlyContinue
        $flaskRunning = $true
        Add-ValidationResult "API" $endpoint $true "✓ Responding"
    } catch {
        if ($flaskRunning -or $_.Exception.Message -like "*refused*") {
            Add-ValidationResult "API" $endpoint $false "Flask not running (that's OK for now)"
            break
        } else {
            Add-ValidationResult "API" $endpoint $false "Error: $($_.Exception.Message)"
        }
    }
}

# ============================================================================
# 9. Summary and Recommendations
# ============================================================================
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   Validation Results" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

if ($allPassed) {
    Write-Host "✓ ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your Node-RED installation is ready to use." -ForegroundColor Green
} else {
    Write-Host "⚠ SOME CHECKS FAILED" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Review the failures above. Common fixes:" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Configure Email:" -ForegroundColor White
Write-Host "   Copy and edit: .env.node-red.example → .env.node-red" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start Node-RED:" -ForegroundColor White
Write-Host "   powershell -ExecutionPolicy Bypass -File .\setup-node-red.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Open Node-RED Editor:" -ForegroundColor White
Write-Host "   http://127.0.0.1:1880" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Test Reports:" -ForegroundColor White
Write-Host "   Click 'Manual Daily (Test)' button to send test email" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Review Documentation:" -ForegroundColor White
Write-Host "   - NODE_RED_COMPLETE_GUIDE.md (full setup)" -ForegroundColor Gray
Write-Host "   - NODE_RED_QUICK_REFERENCE.md (quick tips)" -ForegroundColor Gray
Write-Host ""

Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to exit"

