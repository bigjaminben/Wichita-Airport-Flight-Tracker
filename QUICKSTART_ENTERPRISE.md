# Quick Start Guide - Enterprise Setup

## TL;DR - Get Running in 3 Steps

### 1. Install Service (Run as Admin)
```powershell
.\install_service.ps1
```

### 2. Setup Automated Tasks (Run as Admin)
```powershell
.\setup_tasks.ps1
```

### 3. Access Dashboard
Open: http://127.0.0.1:5001/static/index.html

---

## What You Get

✅ **24/7 Operation**: Windows Service that runs continuously  
✅ **Auto-Restart**: Service recovers automatically from failures  
✅ **Hourly Backups**: Database backed up every hour  
✅ **Daily Backups**: Full backup at 2 AM daily  
✅ **Weekly Backups**: Sunday at 3 AM  
✅ **Health Monitoring**: Checks every 5 minutes  
✅ **Log Rotation**: Automatic log management  
✅ **Data Archival**: Old data (90+ days) archived automatically  
✅ **Compression**: Old backups compressed to save space  

---

## Service Commands

```powershell
# View status
Get-Service ICTFlightTracker

# Start/Stop/Restart
Start-Service ICTFlightTracker
Stop-Service ICTFlightTracker
Restart-Service ICTFlightTracker

# View logs
Get-Content logs\service.log -Tail 50 -Wait
```

---

## File Structure

```
Your Folder/
├── service_wrapper.py          # Windows Service
├── backup_manager.py           # Automated backups
├── health_monitor.py           # Health monitoring
├── install_service.ps1         # Installation script
├── uninstall_service.ps1       # Uninstall script
├── setup_tasks.ps1             # Setup scheduled tasks
├── logs/                       # All logs here
│   ├── service.log            # Service activity
│   ├── application.log        # App activity
│   ├── errors.log             # Errors only
│   ├── health.log             # Health checks
│   └── health_status.json     # Current status
└── backups/                    # All backups here
    ├── flight_history_hourly_*.db
    ├── flight_history_daily_*.db
    ├── flight_history_weekly_*.db
    └── archive/                # Archived data (90+ days)
```

---

## Backup Schedule

| Type    | Frequency        | Retention   |
|---------|------------------|-------------|
| Hourly  | Every hour       | 24 hours    |
| Daily   | 2:00 AM          | 30 days     |
| Weekly  | Sunday 3:00 AM   | 12 weeks    |
| Archive | Sunday 6:00 AM   | Indefinite  |

**Auto-Compression**: Backups older than 7 days are compressed to `.gz`

---

## Monitoring

**Health checks every 5 minutes:**
- ✓ Is API responding?
- ✓ Is database accessible?
- ✓ CPU/Memory/Disk usage
- ✓ Are backups current?

**View current health:**
```powershell
Get-Content logs\health_status.json
```

---

## Troubleshooting

### Service won't start?
```powershell
Get-Content logs\service.log -Tail 50
Restart-Service ICTFlightTracker
```

### Dashboard not loading?
1. Check service: `Get-Service ICTFlightTracker`
2. Check port: `netstat -ano | findstr :5001`
3. Try: http://127.0.0.1:5001/static/index.html

### Need to uninstall?
```powershell
.\uninstall_service.ps1
```

---

## Full Documentation

See `ENTERPRISE_DEPLOYMENT.md` for complete details on:
- Manual backup/restore procedures
- Data retention policies
- Performance optimization
- Security recommendations
- Advanced troubleshooting

---

**Dashboard URL**: http://127.0.0.1:5001/static/index.html  
**Service Name**: ICTFlightTracker  
**Auto-Start**: Yes (starts with Windows)
