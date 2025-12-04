# Airport Tracker — Live Flight Dashboard

A real-time flight tracking application with live OpenSky Network data, weather forecasts, and professional visualizations. Includes both a terminal-based menu app and a modern web UI with interactive Plotly charts.

## 🚀 Quick Start (One Command!)

```powershell
cd "C:\Users\basmussen\Desktop\Flight Trackers\New folder"
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

✅ This does everything:
- Checks Python 3.10+
- Installs dependencies (one-time)
- Downloads brand logo
- Starts production server on http://127.0.0.1:5001
- Opens the web UI automatically in your browser
- Press **Ctrl+C** to stop

---

## 📊 What You'll See

### Web UI Dashboard (http://127.0.0.1:5001)
- **Interactive Plotly Charts**:
  - Flight Status (pie chart)
  - Hourly Activity (line chart)
  - Airline On-Time Performance (bar chart)
  - Live Aircraft Map (scattergeo plot with lat/lon)
- **Matplotlib Plots** (sidebar buttons):
  - Comprehensive 6-panel dashboard
  - Individual visualizations (runway, delays, weather, etc.)
- **Live JSON Data**:
  - Real flights and weather (first 50 flights shown)
  - Updates every 15 seconds

---

## 🛠 Installation & Dependencies

If `start.ps1` fails, install manually:

```powershell
py -3 -m pip install -r requirements.txt
```

**Required packages**:
- Flask>=2.0 (REST API)
- Plotly (interactive charts)
- Pandas, NumPy (data handling)
- Matplotlib, Seaborn (professional plots)
- Requests (HTTP calls)
- Waitress (production WSGI server)
- Pillow (image processing for logo overlay)

---

## Alternative: Terminal-Based App

For the classic terminal menu interface:

```powershell
py -3 "Airport Tracker.py"
```

Interactive menu with:
- Arrivals & departures boards
- Flight status and delays
- Weather comparison
- 7 professional matplotlib plots

---

## ⚙️ Advanced: Background Running

### Run in Background (Hidden Window)
```powershell
.\start_background.ps1
```

### Auto-Start at Windows Logon
Install scheduled task:
```powershell
.\install_schtask.ps1
```

Remove scheduled task:
```powershell
.\uninstall_schtask.ps1
```

---

## 📡 Data Sources

- **Flights**: [OpenSky Network API](https://opensky-network.org/api/) — Free real-time ADS-B data
- **Weather**: [Open-Meteo API](https://open-meteo.com/) — Free weather forecasts
- **Coverage**: Wichita area (ICT) + extended US weather data

---

## 🔍 Troubleshooting

**"Connection refused" error?**
- Check Windows Firewall allows port 5001
- Ensure no other app is using that port

**"ModuleNotFoundError"?**
- Run: `py -3 -m pip install -r requirements.txt`

**No live data showing?**
- External APIs (OpenSky, Open-Meteo) might be rate-limited or down
- UI will retry every 15 seconds automatically

**PowerShell script errors?**
- Use: `powershell -ExecutionPolicy Bypass -File .\start.ps1`

---

## 📁 Project Structure

```
Flight Trackers/
├── Airport Tracker.py         # Main tracker class + matplotlib charts
├── api.py                     # Flask REST API + static UI server
├── serve_prod.py              # Production WSGI server (Waitress)
├── start.ps1                  # One-command launcher
├── download_logo.py           # Logo downloader
├── requirements.txt           # Python dependencies
├── run_server.ps1             # Alternative launch script
├── start_background.ps1       # Background runner
├── install_schtask.ps1        # Scheduled task installer
├── uninstall_schtask.ps1      # Scheduled task remover
├── static/
│   ├── index.html             # Web UI
│   ├── app.js                 # Plotly charts + refresh logic
│   ├── styles.css             # Responsive styling
│   └── logo.png               # Brand logo (auto-downloaded)
└── README.md                  # This file
```

---

**Enjoy your Airport Tracker! 🛫**
