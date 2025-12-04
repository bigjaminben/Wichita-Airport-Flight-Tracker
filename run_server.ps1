param(
    [int]$Port = 5001
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

# Find Python executable
$pythonCmd = "py"  # Windows Python launcher (preferred)
try {
    & $pythonCmd --version >$null 2>&1
} catch {
    # Fall back to checking PATH
    $pythonExe = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonExe) {
        $pythonCmd = $pythonExe.Source
    } else {
        Write-Host "ERROR: Python not found. Please install Python or add it to PATH." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Using Python: $pythonCmd"
Write-Host "Installing Python requirements (may take a moment)..."
& $pythonCmd -m pip install -r "$root\requirements.txt"

# Attempt to download the brand logo into static/logo.png (non-fatal)
try {
    Write-Host "Downloading brand logo to static/logo.png..."
    & $pythonCmd download_logo.py
} catch {
    Write-Host "Could not download logo (continuing)" -ForegroundColor Yellow
}

Write-Host "Starting Airport Tracker API on port $Port..."
try {
    # Try to add a firewall rule to allow inbound on the chosen port (requires admin rights)
    $ruleName = "Airport Tracker Port $Port"
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if (-not $existing) {
        Write-Host "Adding temporary firewall rule to allow inbound TCP port $Port (requires admin)..."
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $Port -Protocol TCP -Action Allow -Profile Any -ErrorAction Stop
        Write-Host "Firewall rule added: $ruleName"
    } else {
        Write-Host "Firewall rule already exists: $ruleName"
    }
} catch {
    Write-Host "Could not add firewall rule (you may need to run as Administrator). Continuing without it." -ForegroundColor Yellow
}

Write-Host "Launching server (logs will appear in this window). Press Ctrl+C to stop."
# Run the production WSGI server (serve_prod.py) with unbuffered output
& $pythonCmd -u serve_prod.py --host 127.0.0.1 --port $Port

Write-Host "Server process exited. If you want the server to keep running in background, run it with Start-Process or create a scheduled task."
