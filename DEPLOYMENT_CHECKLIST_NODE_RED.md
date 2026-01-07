# Node-RED Deployment Checklist
## Production Deployment Guide for Flight Tracker

**Project:** ICT Airport Flight Tracker  
**Component:** Node-RED Email Automation  
**Date:** December 23, 2025  

---

## Pre-Deployment Checklist

### ✓ Prerequisites (Before Starting)
- [ ] Windows 7 SP1 or later
- [ ] 256 MB RAM available
- [ ] Python 3.10+ installed and working
- [ ] Flask API can start successfully
- [ ] Wired internet connection (recommended)
- [ ] Administrator access on this computer

### ✓ Installation (Week 1)
- [ ] Run `setup-node-red.ps1`
- [ ] All packages installed successfully
- [ ] `validate-node-red-setup.ps1` shows all green ✓
- [ ] `.node-red` directory exists with `flows.json`
- [ ] Node-RED starts without errors

### ✓ Email Configuration (Week 1)
- [ ] Gmail account with 2FA enabled
- [ ] App password generated (16 characters)
- [ ] SMTP credentials verified
- [ ] Test email account configured (e.g., test@gmail.com)
- [ ] Email provider settings documented

### ✓ Node-RED Setup (Week 1)
- [ ] Node-RED running on http://127.0.0.1:1880
- [ ] Flows visible in editor
- [ ] Email nodes configured with credentials
- [ ] All nodes connected without errors
- [ ] Debug panel enabled and visible

### ✓ Testing (Week 1)
- [ ] Click "Manual Daily (Test)" button
- [ ] Receive test email within 10 seconds
- [ ] Email HTML formatting looks good
- [ ] All data fields populated correctly
- [ ] Click "Manual Weekly (Test)" button
- [ ] Receive test weekly report
- [ ] Weekly email shows 7-day statistics
- [ ] Check spam folder (email not filtered)
- [ ] Test with at least 2 different email addresses

### ✓ Flask API Verification (Week 1)
- [ ] Flask API running on http://127.0.0.1:5001
- [ ] `/api/report/daily` endpoint returns data
- [ ] `/api/report/weekly` endpoint returns data
- [ ] `/api/report/executive-summary` responds
- [ ] `/api/node-red/health` shows "healthy"
- [ ] All endpoints have valid JSON responses

### ✓ Scheduling (Week 2)
- [ ] Daily schedule cron expression entered
- [ ] Weekly schedule cron expression entered
- [ ] Schedules reviewed by supervisor/manager
- [ ] Backup schedule set (if needed)
- [ ] Team notified of report times
- [ ] Calendar marked with report times
- [ ] Alert set 1 hour before first automated report

---

## Deployment Options

### Option A: Windows Service (Recommended for 24/7)

#### Installation Steps
- [ ] Run as Administrator: PowerShell
- [ ] Execute: `.\install_node_red_service.ps1`
- [ ] Installation completes without errors
- [ ] Service named "NodeRED - ICT Airport Reports" appears
- [ ] Service automatically starts
- [ ] Service starts on Windows boot
- [ ] Verify with: `Get-Service | Where-Object { $_.DisplayName -like '*node*red*' }`

#### Service Verification
- [ ] Windows service shows "Running" status
- [ ] Node-RED accessible at http://127.0.0.1:1880
- [ ] Manual tests still work
- [ ] Service doesn't consume excessive CPU
- [ ] Memory usage stable (~256 MB)

**Selected:** ☐ Yes ☐ No

---

### Option B: Scheduled Task (Alternative)

#### Setup Steps
- [ ] Open Windows Task Scheduler
- [ ] Create new task "Node-RED"
- [ ] Trigger: "At system startup"
- [ ] Action: Start program `node-red`
- [ ] Set to run with highest privileges
- [ ] Set restart on failure

#### Verification
- [ ] Task shows in Task Scheduler
- [ ] Task runs after system restart
- [ ] Node-RED accessible at http://127.0.0.1:1880
- [ ] Manual tests work

**Selected:** ☐ Yes ☐ No

---

### Option C: Startup Script (Manual)

#### Setup Steps
- [ ] Create shortcut to `start_node_red.ps1`
- [ ] Add to Windows Startup folder: `C:\Users\USERNAME\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`
- [ ] Set to run as Administrator
- [ ] Test by restarting computer

#### Verification
- [ ] Script runs on startup
- [ ] Node-RED window appears
- [ ] Accessible at http://127.0.0.1:1880

**Selected:** ☐ Yes ☐ No

---

## Production Readiness

### ✓ Monitoring Setup
- [ ] Team member assigned to monitor emails
- [ ] Backup monitor assigned (for absences)
- [ ] Escalation contact documented
- [ ] Error notification email configured
- [ ] First email received by entire team
- [ ] Team reviews first 3 automated reports
- [ ] Feedback collected and documented

### ✓ Backup & Recovery
- [ ] `flows.json` backed up to network drive
- [ ] `.env.node-red` backed up securely
- [ ] Recovery procedure documented
- [ ] Recovery tested successfully
- [ ] Recovery time target (RTO) set
- [ ] Contact list for emergency support

### ✓ Documentation Deployment
- [ ] `NODE_RED_QUICK_REFERENCE.md` shared with team
- [ ] Support contacts documented
- [ ] How to restart Node-RED documented
- [ ] How to change email recipients documented
- [ ] Emergency contact information posted
- [ ] Team trained on basic troubleshooting

### ✓ Performance Baseline
- [ ] First week email delivery times recorded
- [ ] No reports are missing
- [ ] Email format consistent
- [ ] Report generation time < 30 seconds
- [ ] No errors in debug panel
- [ ] Memory usage stable
- [ ] CPU usage < 5% when idle

---

## Go-Live Checklist

### Phase 1: Small Group (Week 2)
- [ ] Deploy to 2-3 person pilot team
- [ ] Collect feedback for 1 week
- [ ] Document any issues
- [ ] Make adjustments as needed
- [ ] Pilot team signs off on system

### Phase 2: Department (Week 3)
- [ ] Expand to full department
- [ ] Train department on use
- [ ] Monitor for 1 week
- [ ] Collect feedback
- [ ] Adjust schedules as needed
- [ ] Department manager approves

### Phase 3: Organization (Week 4)
- [ ] Full deployment across organization
- [ ] Post documentation on intranet
- [ ] Conduct team meeting explaining system
- [ ] Schedule follow-up check-in (1 week, 1 month)
- [ ] Get executive approval

### Phase 4: Ongoing (Ongoing)
- [ ] Monitor email delivery daily for 1 month
- [ ] Check email formatting on multiple devices
- [ ] Review team feedback monthly
- [ ] Adjust reports as needed
- [ ] Update documentation as needed

---

## Post-Deployment (First Month)

### Week 1 After Deployment
- [ ] All automated reports arrived on time
- [ ] No missed reports
- [ ] No duplicate reports sent
- [ ] Email formatting correct on all devices
- [ ] Collect initial user feedback
- [ ] Address any urgent issues

### Week 2 After Deployment
- [ ] Continue monitoring delivery
- [ ] Review email content with stakeholders
- [ ] Get feedback on data quality
- [ ] Verify schedules are correct
- [ ] Check service resource usage

### Week 3 After Deployment
- [ ] No issues reported
- [ ] User satisfaction confirmed
- [ ] Service stability confirmed
- [ ] Performance metrics normal
- [ ] Plan for long-term monitoring

### Week 4 After Deployment
- [ ] Conduct post-deployment review
- [ ] Document lessons learned
- [ ] Update runbooks
- [ ] Archive first month's emails
- [ ] Schedule quarterly reviews

---

## Ongoing Maintenance

### Daily (System Administrator)
- [ ] Check that both reports sent (if scheduled for today)
- [ ] Verify no errors in Windows Event Log
- [ ] Quick visual check of Node-RED UI

### Weekly (System Administrator)
- [ ] Review all emails sent during week
- [ ] Check Node-RED debug panel for warnings
- [ ] Verify service is running: `Get-Service`
- [ ] Check disk space available
- [ ] Monitor performance stats

### Monthly (System Administrator)
- [ ] Review system logs
- [ ] Collect user feedback
- [ ] Test manual report triggers
- [ ] Backup flows.json and config
- [ ] Review and update documentation
- [ ] Plan any schedule adjustments
- [ ] Check for Node.js or package updates

### Quarterly (IT & Leadership)
- [ ] Security review
- [ ] Performance analysis
- [ ] Cost analysis
- [ ] Disaster recovery test
- [ ] Update stakeholders
- [ ] Plan for improvements

---

## Success Metrics

### Delivery
- [x] 100% of automated reports sent
- [x] 0% reports sent to wrong recipients
- [x] 0% duplicate reports
- [x] < 30 second generation time
- [x] Email arrives within 1 minute of generation

### Quality
- [x] All data fields populate correctly
- [x] Email renders correctly on mobile/desktop
- [x] HTML formatting preserved
- [x] Subject lines clear and professional
- [x] Timestamps accurate

### Reliability
- [x] 99.9% uptime over 30 days
- [x] 0 unplanned outages
- [x] 0 data loss incidents
- [x] Service auto-restarts on failure
- [x] No manual intervention needed

### User Satisfaction
- [x] 100% of reports read (if tracked)
- [x] Positive feedback from users
- [x] No support tickets about reports
- [x] Usage remains consistent
- [x] No request to disable system

---

## Contingency Plans

### If Email Not Sending

**Problem:** Manual tests work but scheduled reports don't send

**Troubleshooting:**
1. Check Windows Event Log for Node-RED service errors
2. Verify Flask API still running (`http://127.0.0.1:5001`)
3. Test manual buttons in Node-RED UI
4. Check SMTP server status with email provider
5. Review debug panel in Node-RED for errors

**Recovery:**
- [ ] Restart Node-RED service: `net restart "NodeRED - ICT Airport Reports"`
- [ ] Check email credentials haven't expired
- [ ] Verify firewall hasn't blocked SMTP port
- [ ] Test with `telnet smtp.gmail.com 587`

### If Node-RED Crashes

**Problem:** Service stops running

**Troubleshooting:**
1. Check Windows Event Log
2. Check disk space available
3. Verify Python API still running
4. Check for Node.js process errors
5. Monitor memory usage during startup

**Recovery:**
- [ ] Manual restart: `net start "NodeRED - ICT Airport Reports"`
- [ ] Reboot server if restart fails
- [ ] Increase memory limit if memory-related
- [ ] Review system resources (disk, RAM, CPU)

### If Flask API Fails

**Problem:** Node-RED can't reach Flask API

**Troubleshooting:**
1. Verify Flask still running: `curl http://127.0.0.1:5001`
2. Check if port changed
3. Look for Python errors in terminal
4. Verify network connectivity
5. Check Windows Firewall rules

**Recovery:**
- [ ] Restart Flask API (`serve_prod.py`)
- [ ] Verify no port conflicts
- [ ] Check firewall allows port 5001
- [ ] Review Flask error logs

### If Service Won't Start

**Problem:** Windows service fails to start

**Troubleshooting:**
1. Check Windows Event Log for specific error
2. Verify Node.js/npm still installed
3. Check for corrupted flows.json
4. Verify user permissions

**Recovery:**
- [ ] Uninstall service and reinstall
- [ ] Restore flows.json from backup
- [ ] Run Node-RED manually to debug
- [ ] Check Node.js version compatibility

---

## Approval & Sign-Off

### Project Manager Approval
- [ ] Name: ________________
- [ ] Date: ________________
- [ ] Signature: ________________

### IT Manager Approval
- [ ] Name: ________________
- [ ] Date: ________________
- [ ] Signature: ________________

### Department Manager Approval
- [ ] Name: ________________
- [ ] Date: ________________
- [ ] Signature: ________________

---

## Contact Information

### Support Contacts
- **Primary:** ________________ ________________
- **Backup:** ________________ ________________
- **Manager:** ________________ ________________

### Documentation Locations
- Node-RED Guide: `NODE_RED_COMPLETE_GUIDE.md`
- Quick Reference: `NODE_RED_QUICK_REFERENCE.md`
- Troubleshooting: `NODE_RED_COMPLETE_GUIDE.md` Section 9
- API Docs: `api.py` comments

### Key Files Location
- Flows: `C:\Users\<USERNAME>\.node-red\flows.json`
- Config: `<PROJECT>\\.env.node-red`
- Logs: Windows Event Log > Application

---

## Notes & Comments

```
[Space for deployment notes, decisions, and comments]




```

---

**Deployment Ready:** ☐ Yes ☐ No  
**Approved for Production:** ☐ Yes ☐ No  
**Date Approved:** ________________

---

**Document Version:** 1.0.0  
**Last Updated:** December 23, 2025  
**Created For:** ICT Airport Flight Tracker Project  

