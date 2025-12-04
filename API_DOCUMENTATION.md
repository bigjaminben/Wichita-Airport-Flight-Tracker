# Airport Tracker - API Documentation

## Overview
The Airport Tracker provides comprehensive flight data aggregation from multiple sources including Flightradar24, Airportia, OpenSky Network, and Open-Meteo weather data.

## Base URL
```
http://127.0.0.1:5001
```

## API Endpoints

### Flight Data

#### GET `/api/flights/all`
Get aggregated flights from all sources (Flightradar24, Airportia, OpenSky).

**Response:**
```json
{
  "flights": [
    {
      "Flight_Number": "UAL123",
      "Airline": "United Airlines",
      "Origin": "ORD",
      "Destination": "ICT",
      "Type": "Arrival",
      "Status": "En Route",
      "latitude": 37.65,
      "longitude": -97.43,
      "altitude": 5000,
      "ground_speed": 250,
      "aircraft_type": "B738",
      "source": "Flightradar24"
    }
  ],
  "count": 15,
  "sources": ["Flightradar24", "Airportia", "OpenSky"],
  "timestamp": 1733328000.0
}
```

#### GET `/api/flights/flightradar24`
Get real-time flight data from Flightradar24 only.

**Response:**
```json
{
  "flights": [...],
  "count": 10,
  "source": "Flightradar24",
  "timestamp": 1733328000.0
}
```

#### GET `/api/flights/airportia`
Get arrivals and departures scraped from Airportia.

**Response:**
```json
{
  "arrivals": [...],
  "departures": [...],
  "arrivals_count": 12,
  "departures_count": 15,
  "source": "Airportia",
  "timestamp": 1733328000.0
}
```

#### GET `/api/flights` (Legacy)
Get flights from original OpenSky integration.

**Response:**
```json
[
  {
    "Flight_Number": "UAL123",
    "Origin": "USA",
    "Type": "Arrival",
    ...
  }
]
```

### Weather Data

#### GET `/api/weather`
Get weather data from Open-Meteo for Wichita area airports.

**Response:**
```json
{
  "ICT": {
    "temperature": 72,
    "conditions": "Clear",
    "wind_speed": 10,
    "visibility": 10
  },
  ...
}
```

### Airport Information

#### GET `/api/airport/info`
Get comprehensive Wichita Airport (ICT) information.

**Response:**
```json
{
  "code": "ICT",
  "name": "Wichita Dwight D. Eisenhower National Airport",
  "city": "Wichita",
  "state": "Kansas",
  "country": "USA",
  "latitude": 37.6499,
  "longitude": -97.4331,
  "elevation_ft": 1333,
  "timezone": "America/Chicago",
  "runways": [
    {
      "id": "01L/19R",
      "length_ft": 10301,
      "width_ft": 150
    }
  ],
  "terminals": 1,
  "gates": 16,
  "airlines_count": 7,
  "links": {
    "official": "https://www.flywichita.com/",
    "flightradar24": "https://www.flightradar24.com/airport/ict"
  }
}
```

#### GET `/api/airport/nas-status`
Get National Airspace System status from FAA.

**Response:**
```json
{
  "status": "Normal",
  "delays": [],
  "timestamp": 1733328000.0
}
```

### Statistics

#### GET `/api/statistics/bts`
Get Bureau of Transportation Statistics data structure (placeholder for future CSV integration).

**Response:**
```json
{
  "airport": "ICT",
  "passenger_stats": {
    "monthly_enplanements": null,
    "yearly_total": null,
    "year_over_year_change": null
  },
  "airline_performance": {
    "on_time_percentage": null,
    "cancellation_rate": null
  },
  "financial_data": {
    "baggage_fees": {},
    "change_fees": {},
    "fuel_costs": {}
  },
  "source": "BTS (placeholder)",
  "note": "BTS data requires CSV import or API key"
}
```

### Matplotlib Plots

#### GET `/api/plot/<name>`
Generate and return a matplotlib plot as PNG image.

**Available plots:**
- `status_pie` - Flight status pie chart
- `airline_bar` - Airline performance bar chart
- `hourly` - Hourly flight activity
- `weather` - Weather comparison
- `runway` - Runway utilization
- `delays` - Delay analysis
- `dashboard` - Comprehensive 6-panel dashboard

**Example:**
```
GET /api/plot/dashboard
```

Returns: PNG image with Deloitte logo overlay

## Data Sources

### 1. Flightradar24
- **URL**: `https://data-cloud.flightradar24.com/zones/fcgi/feed.js`
- **Coverage**: Real-time aircraft positions worldwide
- **Update Frequency**: ~1 second
- **Data Includes**: Flight number, aircraft type, altitude, speed, position, origin/destination

### 2. Airportia
- **URLs**: 
  - Arrivals: `https://www.airportia.com/united-states/wichita-mid-continent-airport/arrivals/`
  - Departures: `https://www.airportia.com/united-states/wichita-mid-continent-airport/departures/`
- **Coverage**: Live arrival and departure boards for ICT
- **Update Frequency**: ~30 seconds
- **Data Includes**: Flight number, airline, origin/destination, scheduled time, status

### 3. OpenSky Network
- **URL**: `https://opensky-network.org/api/states/all`
- **Coverage**: Crowdsourced ADS-B flight data
- **Update Frequency**: ~10 seconds
- **Data Includes**: Callsign, position, altitude, velocity

### 4. Open-Meteo
- **URL**: `https://api.open-meteo.com/v1/forecast`
- **Coverage**: Weather forecasts for airport coordinates
- **Update Frequency**: Hourly
- **Data Includes**: Temperature, precipitation, current conditions

### 5. FAA NAS Status (Future)
- **URL**: `https://nasstatus.faa.gov/api/airport-status-information`
- **Coverage**: National Airspace System delays and closures
- **Update Frequency**: Real-time

### 6. Bureau of Transportation Statistics (Placeholder)
- **URLs**: Various BTS Transtats endpoints
- **Coverage**: Historical passenger data, airline performance, financial statistics
- **Note**: Requires CSV download or API key (not yet implemented)

## Caching

All endpoints implement 15-second in-memory caching to prevent API rate limiting:
- Flight data cached for 15s
- Weather data cached for 15s
- Plots cached for 15s

## Rate Limits

**External API Limits:**
- Flightradar24: ~100 requests/hour (unofficial)
- OpenSky Network: 400 requests/day (anonymous)
- Open-Meteo: 10,000 requests/day (free tier)
- Airportia: No official limit (web scraping, use responsibly)

**Recommendation:** Use the built-in 15s caching and avoid excessive manual refreshes.

## Error Handling

All endpoints return JSON with error messages on failure:
```json
{
  "error": "Error description",
  "flights": []
}
```

HTTP status codes:
- `200` - Success
- `404` - Endpoint not found
- `500` - Internal server error

## Web UI

Access the interactive dashboard at:
```
http://127.0.0.1:5001/
```

Features:
- Real-time Plotly charts
- Tabbed arrivals/departures view
- Multiple data source selection
- Auto-refresh every 15 seconds
- Matplotlib plot preview with logo overlay

## Example Usage

### JavaScript
```javascript
// Fetch all flights
const response = await fetch('http://127.0.0.1:5001/api/flights/all');
const data = await response.json();
console.log(`Found ${data.count} flights from ${data.sources.join(', ')}`);

// Fetch Flightradar24 only
const fr24 = await fetch('http://127.0.0.1:5001/api/flights/flightradar24');
const fr24Data = await fr24.json();

// Get airport info
const info = await fetch('http://127.0.0.1:5001/api/airport/info');
const airportInfo = await info.json();
console.log(airportInfo.name);
```

### Python
```python
import requests

# Get all flights
response = requests.get('http://127.0.0.1:5001/api/flights/all')
data = response.json()
print(f"Found {data['count']} flights")

# Get Airportia arrivals/departures
airportia = requests.get('http://127.0.0.1:5001/api/flights/airportia')
arrivals = airportia.json()['arrivals']
print(f"{len(arrivals)} arrivals")

# Download a plot
plot = requests.get('http://127.0.0.1:5001/api/plot/dashboard')
with open('dashboard.png', 'wb') as f:
    f.write(plot.content)
```

### cURL
```bash
# Get all flights
curl http://127.0.0.1:5001/api/flights/all

# Get weather
curl http://127.0.0.1:5001/api/weather

# Download plot
curl http://127.0.0.1:5001/api/plot/status_pie > status.png
```

## Future Enhancements

- [ ] BTS CSV data import integration
- [ ] Airline baggage fee database
- [ ] Flight delay prediction model
- [ ] Historical trend analysis
- [ ] Email/SMS alerts for flight status changes
- [ ] Mobile-responsive PWA version
- [ ] WebSocket real-time updates
- [ ] Custom airport selection (beyond ICT)
