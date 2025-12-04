const REFRESH_MS = 15000;

async function fetchData() {
  try {
    // Fetch aggregated data and history
    const [flightsAllRes, weatherRes, historyRes] = await Promise.all([
      fetch('/api/flights/all'),
      fetch('/api/weather'),
      fetch('/api/flights/history')
    ]);
    
    const flightsAll = await flightsAllRes.json();
    const weather = await weatherRes.json();
    const history = await historyRes.json();

    // Extract flights array (includes Flightradar24 + Airportia aggregated)
    const flights = flightsAll.flights || [];
    
    // Properly separate arrivals and departures - strict filtering
    const arrivals = flights.filter(f => f.Type === 'Arrival' && f.Destination === 'ICT');
    const departures = flights.filter(f => f.Type === 'Departure' && f.Origin === 'ICT');
    
    // Update stat cards
    document.getElementById('total-flights').textContent = arrivals.length + departures.length;
    document.getElementById('total-arrivals').textContent = arrivals.length;
    document.getElementById('total-departures').textContent = departures.length;
    document.getElementById('flight-count').textContent = arrivals.length + departures.length;
    
    // Display arrivals and departures in formatted cards (now includes live arriving aircraft)
    renderFlightList('arrivals-list', arrivals, 'arrival');
    renderFlightList('departures-list', departures, 'departure');
    
    // Display historical status breakdown
    renderHistoryStats(history);
    
    // Render weather cards
    renderWeatherCards(weather);
    
    document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();

    // Build interactive charts using Plotly
    buildStatusChart(flights);
    buildHourlyChart(flights);
    buildAirlineChart(flights);
    buildMapChart(flights);
  } catch (e) {
    console.error('Error fetching data:', e);
    const errorMsg = `<div class="error-state">Error fetching flights: ${e.message}</div>`;
    document.getElementById('arrivals-list').innerHTML = errorMsg;
    document.getElementById('departures-list').innerHTML = errorMsg;
  }
}

function renderFlightList(elementId, flights, type) {
  const container = document.getElementById(elementId);
  
  if (!flights || flights.length === 0) {
    container.innerHTML = '<div class="empty-state">No flight data available</div>';
    return;
  }
  
  const maxFlights = type === 'radar' ? 15 : 10;
  const flightsToShow = flights.slice(0, maxFlights);
  
  const html = flightsToShow.map(flight => {
    const statusClass = getStatusClass(flight.Status);
    const location = type === 'arrival' ? flight.Origin : 
                     type === 'departure' ? flight.Destination : 
                     `${flight.origin || flight.Origin || 'N/A'} → ${flight.destination || flight.Destination || 'N/A'}`;
    
    // Normalize status display text
    let displayStatus = flight.Status || 'Unknown';
    if (displayStatus.toLowerCase().includes('en-route') || displayStatus.toLowerCase().includes('en route')) {
      displayStatus = 'Arriving';
    }
    if (displayStatus.toLowerCase().includes('track >') || displayStatus === 'Track >') {
      displayStatus = 'Departing';
    }
    
    return `
      <div class="flight-card ${statusClass}">
        <div class="flight-header">
          <span class="flight-number">${flight.Flight_Number}</span>
          <span class="flight-status status-${statusClass}">${displayStatus}</span>
        </div>
        <div class="flight-details">
          <div class="detail-row">
            <span class="label">Airline:</span>
            <span class="value">${flight.Airline || 'Unknown'}</span>
          </div>
          <div class="detail-row">
            <span class="label">${type === 'arrival' ? 'From' : type === 'departure' ? 'To' : 'Route'}:</span>
            <span class="value">${location}</span>
          </div>
          ${flight.Scheduled_Time ? `
          <div class="detail-row">
            <span class="label">Scheduled:</span>
            <span class="value">${flight.Scheduled_Time}</span>
          </div>` : ''}
          ${flight.altitude ? `
          <div class="detail-row">
            <span class="label">Altitude:</span>
            <span class="value">${flight.altitude} ft</span>
          </div>` : ''}
          ${flight.ground_speed ? `
          <div class="detail-row">
            <span class="label">Speed:</span>
            <span class="value">${flight.ground_speed} kts</span>
          </div>` : ''}
        </div>
      </div>
    `;
  }).join('');
  
  container.innerHTML = html;
}

function getStatusClass(status) {
  if (!status) return 'unknown';
  const s = status.toLowerCase();
  if (s.includes('land') || s.includes('arrived')) return 'landed';
  if (s.includes('delay') || s.includes('late')) return 'delayed';
  if (s.includes('cancel')) return 'cancelled';
  if (s.includes('arriving') || s.includes('en-route') || s.includes('en route')) return 'arriving';
  if (s.includes('departing') || s.includes('track')) return 'departing';
  if (s.includes('scheduled')) return 'scheduled';
  return 'unknown';
}

function renderHistoryStats(history) {
  const container = document.getElementById('history-summary');
  if (!container) return; // Element doesn't exist yet
  
  const arrivals = history.arrivals || [];
  const departures = history.departures || [];
  
  // Count statuses for arrivals based on actual status values
  const arrTracked = arrivals.filter(f => f.status && f.status.includes('Track')).length;
  const arrArriving = arrivals.filter(f => f.status && f.status.toLowerCase().includes('arriving')).length;
  const arrDelayed = arrivals.filter(f => f.status && f.status.toLowerCase().includes('delayed')).length;
  const arrCancelled = arrivals.filter(f => f.status && f.status.toLowerCase().includes('cancel')).length;
  
  // Count statuses for departures based on actual status values
  const depTracked = departures.filter(f => f.status && f.status.includes('Track')).length;
  const depDeparting = departures.filter(f => f.status && f.status.toLowerCase().includes('departing')).length;
  const depDelayed = departures.filter(f => f.status && f.status.toLowerCase().includes('delayed')).length;
  const depCancelled = departures.filter(f => f.status && f.status.toLowerCase().includes('cancel')).length;
  
  container.innerHTML = `
    <div class="history-summary-section">
      <h4>📊 Today's Flight Summary</h4>
      <div class="summary-grid">
        <div class="summary-column">
          <h5>🛬 Arrivals (${arrivals.length} total)</h5>
          <div class="status-breakdown">
            <div class="status-item landed">🔵 En Route: ${arrTracked}</div>
            <div class="status-item landed">✈️ Arriving: ${arrArriving}</div>
            <div class="status-item delayed">⏰ Delayed: ${arrDelayed}</div>
            <div class="status-item cancelled">✗ Cancelled: ${arrCancelled}</div>
          </div>
        </div>
        <div class="summary-column">
          <h5>🛫 Departures (${departures.length} total)</h5>
          <div class="status-breakdown">
            <div class="status-item landed">🔵 En Route: ${depTracked}</div>
            <div class="status-item landed">✈️ Departing: ${depDeparting}</div>
            <div class="status-item delayed">⏰ Delayed: ${depDelayed}</div>
            <div class="status-item cancelled">✗ Cancelled: ${depCancelled}</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderWeatherCards(weather) {
  const container = document.getElementById('weather-cards');
  
  if (!weather || Object.keys(weather).length === 0) {
    container.innerHTML = '<div class="empty-state">No weather data available</div>';
    return;
  }
  
  const html = Object.entries(weather).slice(0, 6).map(([airport, data]) => {
    return `
      <div class="weather-card">
        <h5>${airport} - ${data.City || airport}</h5>
        <div class="weather-temp">${data.Temperature_F || 'N/A'}°F</div>
        <div class="weather-details">
          <div>☁️ ${data.Condition || 'Unknown'}</div>
          <div>💨 ${data.Wind_Speed_mph || 'N/A'} mph</div>
          <div>👁️ ${data.Visibility_miles || 'N/A'} mi</div>
          <div>💧 ${data.Humidity_percent || 'N/A'}%</div>
        </div>
      </div>
    `;
  }).join('');
  
  container.innerHTML = html;
}

function buildStatusChart(flights) {
  const counts = {};
  flights.forEach(f => {
    let status = f.Status || 'Unknown';
    // Normalize status names for display
    if (status.toLowerCase().includes('en-route') || status.toLowerCase().includes('en route')) {
      status = 'Arriving';
    }
    if (status.toLowerCase().includes('track >') || status === 'Track >') {
      status = 'Departing';
    }
    counts[status] = (counts[status] || 0) + 1;
  });
  const labels = Object.keys(counts);
  const values = labels.map(l => counts[l]);
  const data = [{ type: 'pie', labels, values, hole: 0.3 }];
  const layout = { title: 'Flight Status Distribution', margin: { t: 40 } };
  layout.images = [{
    source: '/static/logo.png',
    xref: 'paper', yref: 'paper',
    x: 1, y: 0, xanchor: 'right', yanchor: 'bottom',
    sizex: 0.15, sizey: 0.15, opacity: 0.85
  }];
  Plotly.newPlot('chart-status', data, layout, {responsive: true});
}

function buildHourlyChart(flights) {
  const hours = {};
  flights.forEach(f => {
    const t = f.Scheduled_Time || 'N/A';
    if (t !== 'N/A') {
      try {
        const h = parseInt(t.split(':')[0], 10);
        if (!isNaN(h)) hours[h] = (hours[h] || 0) + 1;
      } catch(e) {}
    }
  });
  const xs = Object.keys(hours).map(k => parseInt(k)).sort((a,b) => a-b);
  const ys = xs.map(x => hours[x]);
  const data = [{ x: xs, y: ys, type: 'scatter', mode: 'lines+markers', marker: {color: '#2980b9'} }];
  const layout = { title: 'Hourly Flight Activity', margin: { t: 40 }, xaxis: { title: 'Hour' }, yaxis: { title: 'Flights' } };
  layout.images = [{ source: '/static/logo.png', xref: 'paper', yref: 'paper', x: 1, y: 0, xanchor: 'right', yanchor: 'bottom', sizex: 0.15, sizey: 0.15, opacity: 0.85 }];
  Plotly.newPlot('chart-hourly', data, layout, {responsive: true});
}

function buildAirlineChart(flights) {
  const stats = {};
  flights.forEach(f => {
    const name = (f.Airline || 'Unknown').split(' ')[0];
    if (!stats[name]) stats[name] = { total:0, ontime:0 };
    stats[name].total += 1;
    if (f.Status === 'On Time') stats[name].ontime += 1;
  });
  const names = Object.keys(stats).slice(0,10);
  const vals = names.map(n => (stats[n].ontime / stats[n].total) * 100);
  const data = [{ x: names, y: vals, type: 'bar', marker: {color: '#2ecc71'} }];
  const layout = { title: 'On-Time % by Airline (top 10)', margin: { t: 40 }, yaxis: { title: '%' } };
  layout.images = [{ source: '/static/logo.png', xref: 'paper', yref: 'paper', x: 1, y: 0, xanchor: 'right', yanchor: 'bottom', sizex: 0.15, sizey: 0.15, opacity: 0.85 }];
  Plotly.newPlot('chart-airline', data, layout, {responsive: true});
}

function buildMapChart(flights) {
  // Build a scattergeo map of aircraft using available lat/lon
  const lats = [];
  const lons = [];
  const texts = [];
  flights.forEach(f => {
    const lat = f.latitude || f.Latitude;
    const lon = f.longitude || f.Longitude;
    if (lat && lon) {
      lats.push(lat);
      lons.push(lon);
      const label = `${f.Flight_Number || 'N/A'}\n${f.Airline || ''}\n${f.altitude || 0} ft`;
      texts.push(label);
    }
  });
  const data = [
    {
      type: 'scattergeo',
      mode: 'markers',
      lat: lats,
      lon: lons,
      text: texts,
      marker: { size: 8, color: '#e74c3c', opacity: 0.8 },
      name: 'Aircraft'
    },
    {
      type: 'scattergeo',
      mode: 'markers',
      lat: [37.65],
      lon: [-97.43],
      text: ['Wichita (ICT)'],
      marker: { size: 15, color: '#27ae60', symbol: 'circle' },
      name: 'ICT Airport'
    }
  ];
  const layout = { 
    title: `Aircraft Locations (${lats.length} tracked)`, 
    geo: { 
      scope: 'usa',
      center: { lat: 37.65, lon: -97.43 },
      projection: { scale: 5 }
    }, 
    margin: { t: 40 },
    showlegend: false
  };
  layout.images = [{ source: '/static/logo.png', xref: 'paper', yref: 'paper', x: 1, y: 0, xanchor: 'right', yanchor: 'bottom', sizex: 0.15, sizey: 0.15, opacity: 0.85 }];
  Plotly.newPlot('chart-map', data, layout, {responsive: true});
}

function setupButtons() {
  // Tab switching for arrivals/departures
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      
      // Hide all tabs
      document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
      });
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active');
      });
      
      // Show selected tab
      document.getElementById(tabName).classList.add('active');
      btn.classList.add('active');
    });
  });

  // Refresh button
  document.getElementById('refresh-now').addEventListener('click', () => {
    fetchData();
  });
}

function startAutoRefresh() {
  setInterval(() => {
    fetchData();
  }, REFRESH_MS);
}

window.addEventListener('load', () => {
  setupButtons();
  fetchData();
  startAutoRefresh();
});
