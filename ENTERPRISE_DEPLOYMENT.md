# Enterprise Deployment Guide - ICT Flight Tracker

## Overview

This enterprise deployment includes:
- **Windows Service**: Runs 24/7 with automatic restart on failure
- **Automated Backups**: Hourly, daily, weekly backups with compression and retention policies
- **Health Monitoring**: Continuous monitoring with logging and alerting
- **Data Archival**: Automatic archival of data older than 90 days
- **Log Rotation**: Automatic log management to prevent disk space issues

## Installation Steps

### 1. Install Required Packages

First, ensure you have the Python virtual environment set up:

```powershell
# If not already created
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Install the Windows Service

Run the installation script **as Administrator**:

```powershell
.\install_service.ps1
```

This will:
- Install required Python packages (pywin32, schedule, psutil)
- Create logs and backups directories
- Install the ICT Flight Tracker Windows Service
- Start the service automatically

### 3. Setup Automated Tasks

Run the task setup script **as Administrator**:

```powershell
.\setup_tasks.ps1
```

This creates two scheduled tasks:
- **Backup Manager**: Handles database backups on schedule
- **Health Monitor**: Monitors service health every 5 minutes

## Service Management

### View Service Status

```powershell
Get-Service ICTFlightTracker | Format-List *
```

### Start/Stop Service

```powershell
# Start
Start-Service ICTFlightTracker

# Stop
Stop-Service ICTFlightTracker

# Restart
Restart-Service ICTFlightTracker
```

### View Service Logs

```powershell
# Service logs (Windows Service wrapper)
Get-Content logs\service.log -Tail 50 -Wait

# Application logs (Flask server)
Get-Content logs\application.log -Tail 50 -Wait

# Error logs only
Get-Content logs\errors.log -Tail 50 -Wait

# Health monitor logs
Get-Content logs\health.log -Tail 50 -Wait
```

## Backup System

### Backup Schedule

- **Hourly**: Every hour (keeps last 24)
- **Daily**: 2:00 AM (keeps last 30 days)
- **Weekly**: Sunday 3:00 AM (keeps last 12 weeks)
- **Monthly**: First of month (keeps last 12 months)

### Backup Storage

All backups are stored in the `backups/` directory:
- Recent backups: `backups/flight_history_[type]_[timestamp].db`
- Compressed backups: `backups/flight_history_[type]_[timestamp].db.gz` (after 7 days)
- Archives: `backups/archive/archive_[date].json.gz` (data older than 90 days)

### Manual Backup

To create a manual backup:

```powershell
.\.venv\Scripts\python.exe -c "from backup_manager import BackupManager; BackupManager().create_backup('manual')"
```

### View Backup Statistics

```powershell
.\.venv\Scripts\python.exe -c "from backup_manager import BackupManager; import json; print(json.dumps(BackupManager().get_backup_stats(), indent=2))"
```

## Health Monitoring

### Health Check Frequency

The health monitor runs every 5 minutes and checks:
- **API Health**: Is the Flask server responding?
- **Database Health**: Is the database accessible? How much space?
- **System Resources**: CPU, memory, disk usage
- **Backup Status**: When was the last backup? Are backups current?

### View Current Health Status

```powershell
Get-Content logs\health_status.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Health Alerts

Critical issues are logged to `logs\errors.log` with full details.

## Data Retention

### Database Retention Policy

- **Active Data**: All flights from the last 90 days remain in the main database
- **Archived Data**: Flights older than 90 days are exported to compressed JSON and removed from the database
- **Archive Location**: `backups/archive/archive_[date].json.gz`

### Backup Retention Policy

- **Hourly**: Last 24 hours (1 day)
- **Daily**: Last 30 days
- **Weekly**: Last 12 weeks (84 days)
- **Monthly**: Last 12 months (365 days)
- **Compression**: Backups older than 7 days are compressed to save space

### Manual Data Export

Export a specific date range:

```python
from flight_history import FlightHistoryDB

db = FlightHistoryDB()

# Get flights from specific date range
flights = db.get_flights_by_date_range('2024-12-01', '2024-12-05')

# Get statistics for date range
stats = db.get_date_range_stats('2024-12-01', '2024-12-05')
print(stats)
```

## Accessing the Dashboard

Once the service is running:

**Dashboard URL**: http://127.0.0.1:5001/static/index.html

The dashboard will:
- Auto-refresh every 15 seconds
- Display current flights (live data)
- Show today's historical statistics
- Display route analysis
- Show weather for key airports

## Troubleshooting

### Service Won't Start

1. Check service logs: `Get-Content logs\service.log -Tail 50`
2. Verify Python path: `.\.venv\Scripts\python.exe --version`
3. Check for port conflicts: `netstat -ano | findstr :5001`
4. Restart manually: `Restart-Service ICTFlightTracker`

### Database Growing Too Large

1. Check database size: `(Get-Item flight_history.db).Length / 1MB`
2. Run manual archival: 
   ```powershell
   .\.venv\Scripts\python.exe -c "from backup_manager import BackupManager; BackupManager().export_old_data(30)"
   ```
3. Adjust retention in `backup_manager.py` config

### Disk Space Issues

1. Check backup directory size:
   ```powershell
   (Get-ChildItem backups -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
   ```
2. Compress old backups manually:
   ```powershell
   .\.venv\Scripts\python.exe -c "from backup_manager import BackupManager; BackupManager().compress_old_backups()"
   ```
3. Adjust retention policies in `backup_manager.py`

### API Not Responding

1. Check health status: `Get-Content logs\health_status.json`
2. Restart service: `Restart-Service ICTFlightTracker`
3. Check errors: `Get-Content logs\errors.log -Tail 50`

## Uninstallation

To completely remove the service:

```powershell
# Run as Administrator
.\uninstall_service.ps1

# Optionally remove scheduled tasks
Unregister-ScheduledTask -TaskName "ICT Flight Tracker - Backup Manager" -Confirm:$false
Unregister-ScheduledTask -TaskName "ICT Flight Tracker - Health Monitor" -Confirm:$false
```

This removes the service but preserves:
- Database (`flight_history.db`)
- All backups (`backups/`)
- All logs (`logs/`)
- Application files

## Performance Optimization

### For High-Traffic Environments

1. **Increase backup retention** but compress more aggressively
2. **Archive data more frequently** (e.g., 30 days instead of 90)
3. **Adjust health check frequency** (e.g., every 10 minutes instead of 5)
4. **Enable Redis caching** for API responses

### For Low-Resource Environments

1. **Reduce backup frequency** (daily instead of hourly)
2. **Increase compression threshold** (compress after 3 days instead of 7)
3. **Reduce log retention** (adjust RotatingFileHandler maxBytes)

## Security Recommendations

1. **Restrict API access** to localhost only (current default)
2. **Secure backup directory** with appropriate Windows permissions
3. **Encrypt sensitive data** if storing in backups
4. **Regular security updates** for Python packages: `pip install -r requirements.txt --upgrade`

## Production Checklist

- [ ] Service installed and running
- [ ] Scheduled tasks created and active
- [ ] First backup completed successfully
- [ ] Health monitoring logging properly
- [ ] Dashboard accessible at http://127.0.0.1:5001/static/index.html
- [ ] Logs rotating properly (check after 24 hours)
- [ ] Backups creating on schedule (check after 24 hours)
- [ ] Database size monitored
- [ ] Disk space sufficient for growth

## Contact and Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review health status in `logs/health_status.json`
3. Check backup statistics
4. Verify scheduled task status

---

**Dashboard**: http://127.0.0.1:5001/static/index.html  
**Service Name**: ICTFlightTracker  
**Installation Date**: {Installation will log this automatically}
