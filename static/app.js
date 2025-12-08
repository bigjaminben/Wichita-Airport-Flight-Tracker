const REFRESH_MS = 15000;
let isRefreshing = false;
let chartsInitialized = false;
let lastFlightData = null;
let chartUpdateQueue = [];
const performanceMetrics = { fetchTime: 0, renderTime: 0 };
const requestCache = new Map();
const CACHE_DURATION = 10000; // Cache API responses for 10 seconds

async function fetchWithCache(url) {
  const now = Date.now();
  const cached = requestCache.get(url);
  
  if (cached && (now - cached.timestamp) < CACHE_DURATION) {
    return cached.data;
  }
  
  const response = await fetch(url);
  const data = await response.json();
  requestCache.set(url, { data, timestamp: now });
  return data;
}

async function fetchData() {
  if (isRefreshing) return;
  isRefreshing = true;
  
  const startTime = performance.now();
  
  try {
    // Fetch only essential data in parallel, use cache for others
    const [flightsAllRes, weatherRes, predictionsRes] = await Promise.all([
      fetchWithCache('/api/flights/all'),
      fetchWithCache('/api/weather'),
      fetchWithCache('/api/predictions/all')
    ]);
    
    // Fetch less critical data separately to avoid blocking
    const historyPromise = fetchWithCache('/api/flights/history');
    const opsPromise = fetchWithCache('/api/operations/today');
    
    const flightsAll = flightsAllRes;
    const weather = weatherRes;
    const predictionsData = predictionsRes;

    // Extract flights array and predictions
    const flights = flightsAll.flights || [];
    const predictions = predictionsData.predictions || [];
    
    // Create prediction lookup map
    const predictionMap = {};
    predictions.forEach(p => {
      predictionMap[p.flight_number] = p.prediction;
    });
    
    // Properly separate arrivals and departures - strict filtering
    const arrivals = flights.filter(f => f.Type === 'Arrival' && f.Destination === 'ICT');
    const departures = flights.filter(f => f.Type === 'Departure' && f.Origin === 'ICT');
    
    // Update stat cards
    const totalFlights = document.getElementById('total-flights');
    const totalArrivals = document.getElementById('total-arrivals');
    const totalDepartures = document.getElementById('total-departures');
    const flightCount = document.getElementById('flight-count');
    if (totalFlights) totalFlights.textContent = arrivals.length + departures.length;
    if (totalArrivals) totalArrivals.textContent = arrivals.length;
    if (totalDepartures) totalDepartures.textContent = departures.length;
    if (flightCount) flightCount.textContent = arrivals.length + departures.length;
    
    // Display arrivals and departures in formatted cards (now includes live arriving aircraft)
    renderFlightList('arrivals-list', arrivals, 'arrival', predictionMap);
    renderFlightList('departures-list', departures, 'departure', predictionMap);
    
    // Load less critical data asynchronously
    historyPromise.then(history => renderHistoryStats(history));
    opsPromise.then(operations => renderOperationsLog(operations));
    
    // Calculate route rankings for weather sorting
    const routeRankings = calculateRouteRankings(flights);
    
    // Display route analysis
    renderRouteAnalysis(flights);
    
    // Render weather cards (sorted by route importance)
    renderWeatherCards(weather, routeRankings);
    
    const lastUpdated = document.getElementById('last-updated');
    if (lastUpdated) lastUpdated.textContent = new Date().toLocaleTimeString();
    updateCurrentTime();

    // Only build charts on first load or if data significantly changed
    const shouldRebuildCharts = !chartsInitialized || hasSignificantChange(flights, lastFlightData);
    if (shouldRebuildCharts) {
      requestAnimationFrame(() => {
        buildStatusChart(flights);
        buildHourlyChart(flights);
        buildAirlineChart(flights);
        buildMapChart(flights);
        chartsInitialized = true;
      });
    }
    lastFlightData = flights;
  } catch (e) {
    const errorMsg = `<div class="error-state">Unable to load flight data</div>`;
    const arrivalsList = document.getElementById('arrivals-list');
    const departuresList = document.getElementById('departures-list');
    if (arrivalsList) arrivalsList.innerHTML = errorMsg;
    if (departuresList) departuresList.innerHTML = errorMsg;
  } finally {
    isRefreshing = false;
  }
}

function renderFlightList(elementId, flights, type, predictionMap = {}) {
  const container = document.getElementById(elementId);
  if (!container) return;
  
  if (!flights || flights.length === 0) {
    container.innerHTML = '<div class="empty-state">No flight data available</div>';
    return;
  }
  
  const maxFlights = type === 'radar' ? 15 : 10;
  const flightsToShow = flights.slice(0, maxFlights);
  
  // Use document fragment for better performance
  const fragment = document.createDocumentFragment();
  const tempDiv = document.createElement('div');
  
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
    
    // Get delay prediction
    const prediction = predictionMap[flight.Flight_Number];
    let delayRiskBadge = '';
    if (prediction) {
      const riskLevel = prediction.risk_level;
      const riskScore = prediction.risk_score;
      const confidence = prediction.confidence;
      const factors = prediction.factors || [];
      
      let riskColor = '#86BC25';  // Deloitte green (low)
      let riskIcon = '🟢';
      if (riskLevel === 'High') {
        riskColor = '#ED1C24';  // Red
        riskIcon = '🔴';
      } else if (riskLevel === 'Medium') {
        riskColor = '#FF6900';  // Orange
        riskIcon = '🟡';
      }
      
      const factorsList = factors.length > 0 ? factors.map(f => `<li>${f}</li>`).join('') : '<li>No specific factors</li>';
      
      delayRiskBadge = `
        <div class="delay-risk-badge risk-${riskLevel.toLowerCase()}" style="background-color: ${riskColor}15; border-left: 3px solid ${riskColor};">
          <div class="risk-header">
            <span class="risk-icon">${riskIcon}</span>
            <span class="risk-level">${riskLevel} Delay Risk</span>
            <span class="risk-score">${riskScore}%</span>
          </div>
          <div class="risk-details">
            <div class="risk-confidence">Confidence: ${confidence}%</div>
            <div class="risk-factors">
              <strong>Factors:</strong>
              <ul>${factorsList}</ul>
            </div>
          </div>
        </div>`;
    }
    
    // Calculate transit time metrics
    let transitTimeHtml = '';
    if (flight.Scheduled_Time) {
      const now = new Date();
      const scheduledParts = flight.Scheduled_Time.split(':');
      const scheduledTime = new Date();
      scheduledTime.setHours(parseInt(scheduledParts[0]), parseInt(scheduledParts[1]), 0);
      
      const diffMs = now - scheduledTime;
      const diffMins = Math.floor(diffMs / 60000);
      
      if (type === 'arrival' && flight.Status && flight.Status.toLowerCase().includes('land')) {
        // Already landed - show actual transit time
        transitTimeHtml = `
          <div class="detail-row transit-metric">
            <span class="label">Transit Time:</span>
            <span class="value transit-complete">Completed</span>
          </div>`;
      } else if (diffMins > 0) {
        // In progress or delayed
        const hours = Math.floor(Math.abs(diffMins) / 60);
        const mins = Math.abs(diffMins) % 60;
        const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
        const statusText = diffMins > 15 ? 'Delayed' : 'On Time';
        const statusClass = diffMins > 15 ? 'transit-delayed' : 'transit-ontime';
        
        transitTimeHtml = `
          <div class="detail-row transit-metric">
            <span class="label">In Transit:</span>
            <span class="value ${statusClass}">${timeStr} (${statusText})</span>
          </div>`;
      } else {
        // Scheduled in future
        const hours = Math.floor(Math.abs(diffMins) / 60);
        const mins = Math.abs(diffMins) % 60;
        const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
        transitTimeHtml = `
          <div class="detail-row transit-metric">
            <span class="label">Departs In:</span>
            <span class="value transit-scheduled">${timeStr}</span>
          </div>`;
      }
    }
    
    return `
      <div class="flight-card ${statusClass}">
        <div class="flight-header">
          <span class="flight-number">${flight.Flight_Number}</span>
          <span class="flight-status status-${statusClass}">${displayStatus}</span>
        </div>
        ${delayRiskBadge}
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
          ${transitTimeHtml}
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
  
  // Use faster DOM update
  tempDiv.innerHTML = html;
  container.innerHTML = '';
  container.appendChild(tempDiv);
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
  if (!container) return;
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
      <h4>📊 Today's Complete Flight History</h4>
      <p class="summary-description">All flights tracked since midnight (includes completed flights)</p>
      <div class="summary-grid">
        <div class="summary-column">
          <h5>🛬 Total Arrivals Today: ${arrivals.length}</h5>
          <div class="status-breakdown">
            <div class="status-item landed">🔵 En Route: ${arrTracked}</div>
            <div class="status-item landed">✈️ Arriving: ${arrArriving}</div>
            <div class="status-item delayed">⏰ Delayed: ${arrDelayed}</div>
            <div class="status-item cancelled">✗ Cancelled: ${arrCancelled}</div>
          </div>
        </div>
        <div class="summary-column">
          <h5>🛫 Total Departures Today: ${departures.length}</h5>
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

function calculateRouteRankings(flights) {
  // Count total flight volume per airport (arrivals + departures)
  const airportCounts = {};
  
  flights.forEach(f => {
    if (f.Type === 'Departure' && f.Origin === 'ICT' && f.Destination) {
      airportCounts[f.Destination] = (airportCounts[f.Destination] || 0) + 1;
    }
    if (f.Type === 'Arrival' && f.Destination === 'ICT' && f.Origin) {
      airportCounts[f.Origin] = (airportCounts[f.Origin] || 0) + 1;
    }
  });
  
  // Sort airports by flight count descending
  return Object.entries(airportCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([airport]) => airport);
}

function renderRouteAnalysis(flights) {
  const container = document.getElementById('route-analysis');
  if (!container) return;
  
  if (!flights || flights.length === 0) {
    container.innerHTML = '<div class="empty-state">No route data available</div>';
    return;
  }
  
  // Analyze departure routes (ICT to where) with efficiency metrics
  const departureDestinations = {};
  const departureMetrics = {};
  
  flights.forEach(f => {
    if (f.Type === 'Departure' && f.Origin === 'ICT' && f.Destination) {
      const dest = f.Destination;
      if (!departureDestinations[dest]) {
        departureDestinations[dest] = 0;
        departureMetrics[dest] = { onTime: 0, delayed: 0, total: 0 };
      }
      departureDestinations[dest]++;
      departureMetrics[dest].total++;
      
      // Track on-time performance
      const status = (f.Status || '').toLowerCase();
      if (status.includes('delay')) {
        departureMetrics[dest].delayed++;
      } else if (status.includes('landed') || status.includes('scheduled') || 
                 status.includes('departing') || status.includes('track')) {
        departureMetrics[dest].onTime++;
      }
    }
  });
  
  // Analyze arrival routes (where to ICT) with efficiency metrics
  const arrivalOrigins = {};
  const arrivalMetrics = {};
  
  flights.forEach(f => {
    if (f.Type === 'Arrival' && f.Destination === 'ICT' && f.Origin) {
      const origin = f.Origin;
      if (!arrivalOrigins[origin]) {
        arrivalOrigins[origin] = 0;
        arrivalMetrics[origin] = { onTime: 0, delayed: 0, total: 0 };
      }
      arrivalOrigins[origin]++;
      arrivalMetrics[origin].total++;
      
      // Track on-time performance
      const status = (f.Status || '').toLowerCase();
      if (status.includes('delay')) {
        arrivalMetrics[origin].delayed++;
      } else if (status.includes('landed') || status.includes('scheduled') || 
                 status.includes('arriving') || status.includes('track')) {
        arrivalMetrics[origin].onTime++;
      }
    }
  });
  
  // Sort and get top 5
  const topDepartures = Object.entries(departureDestinations)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  
  const topArrivals = Object.entries(arrivalOrigins)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  
  const departuresHtml = topDepartures.length > 0 
    ? topDepartures.map(([dest, count]) => {
        const metrics = departureMetrics[dest];
        const efficiency = metrics.total > 0 ? Math.round((metrics.onTime / metrics.total) * 100) : 0;
        const efficiencyClass = efficiency >= 80 ? 'efficiency-good' : efficiency >= 60 ? 'efficiency-medium' : 'efficiency-poor';
        
        return `
        <div class="route-item">
          <div class="route-info">
            <span class="route-airport">🛫 ${dest}</span>
            <span class="route-count">${count} flight${count > 1 ? 's' : ''}</span>
          </div>
          <div class="route-metrics">
            <span class="efficiency-badge ${efficiencyClass}">${efficiency}% On-Time</span>
          </div>
        </div>
      `;
      }).join('')
    : '<div class="empty-state">No departure data</div>';
  
  const arrivalsHtml = topArrivals.length > 0
    ? topArrivals.map(([origin, count]) => {
        const metrics = arrivalMetrics[origin];
        const efficiency = metrics.total > 0 ? Math.round((metrics.onTime / metrics.total) * 100) : 0;
        const efficiencyClass = efficiency >= 80 ? 'efficiency-good' : efficiency >= 60 ? 'efficiency-medium' : 'efficiency-poor';
        
        return `
        <div class="route-item">
          <div class="route-info">
            <span class="route-airport">🛬 ${origin}</span>
            <span class="route-count">${count} flight${count > 1 ? 's' : ''}</span>
          </div>
          <div class="route-metrics">
            <span class="efficiency-badge ${efficiencyClass}">${efficiency}% On-Time</span>
          </div>
        </div>
      `;
      }).join('')
    : '<div class="empty-state">No arrival data</div>';
  
  const html = `
    <h3>📊 Route Analysis</h3>
    <div class="route-columns">
      <div class="route-column">
        <h4>Top Departures from ICT</h4>
        <div class="route-list">
          ${departuresHtml}
        </div>
      </div>
      <div class="route-column">
        <h4>Top Arrivals to ICT</h4>
        <div class="route-list">
          ${arrivalsHtml}
        </div>
      </div>
    </div>
  `;
  
  container.innerHTML = html;
}

function renderWeatherCards(weather, routeRankings = []) {
  const container = document.getElementById('weather-cards');
  if (!container) return;
  
  if (!weather || Object.keys(weather).length === 0) {
    container.innerHTML = '<div class="empty-state">No weather data available</div>';
    return;
  }
  
  // Sort weather entries: ICT first, then by route ranking
  const weatherEntries = Object.entries(weather);
  const sortedEntries = weatherEntries.sort((a, b) => {
    const [airportA] = a;
    const [airportB] = b;
    
    // ICT always first
    if (airportA === 'ICT') return -1;
    if (airportB === 'ICT') return 1;
    
    // Then sort by route ranking (if available)
    const rankA = routeRankings.indexOf(airportA);
    const rankB = routeRankings.indexOf(airportB);
    
    // If both have rankings, sort by rank
    if (rankA !== -1 && rankB !== -1) return rankA - rankB;
    
    // If only one has a ranking, prioritize it
    if (rankA !== -1) return -1;
    if (rankB !== -1) return 1;
    
    // Otherwise maintain original order
    return 0;
  });
  
  const html = sortedEntries.slice(0, 8).map(([airport, data]) => {
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
  if (!document.getElementById('chart-status')) return;
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
  const chartDiv = document.getElementById('chart-status');
  if (chartDiv.data) {
    Plotly.react('chart-status', data, layout, {responsive: true, displayModeBar: false});
  } else {
    Plotly.newPlot('chart-status', data, layout, {responsive: true, displayModeBar: false});
  }
}

function buildHourlyChart(flights) {
  if (!document.getElementById('chart-hourly')) return;
  // Get current hour
  const now = new Date();
  const currentHour = now.getHours();
  
  // Create array of last 24 hours (from 24 hours ago to current hour)
  const last24Hours = [];
  for (let i = 23; i >= 0; i--) {
    const hour = (currentHour - i + 24) % 24;
    last24Hours.push(hour);
  }
  
  // Count flights per hour
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
  
  // Build data for last 24 hours in order
  const ys = last24Hours.map(h => hours[h] || 0);
  
  // Format x-axis labels as time in CST (12-hour format)
  const xLabels = last24Hours.map(h => {
    const hour12 = h === 0 ? 12 : (h > 12 ? h - 12 : h);
    const ampm = h < 12 ? 'AM' : 'PM';
    return `${hour12}:00 ${ampm}`;
  });
  
  const data = [{ 
    x: xLabels, 
    y: ys, 
    type: 'bar', 
    marker: {
      color: '#2980b9',
      line: {
        color: '#1a5276',
        width: 1
      }
    },
    hovertemplate: '%{x}<br>%{y} flights<extra></extra>'
  }];
  
  const layout = { 
    title: 'Hourly Flight Activity (Last 24 Hours)', 
    margin: { t: 40, b: 100, l: 60, r: 40 }, 
    xaxis: { 
      title: 'Time (CST)', 
      tickangle: -45,
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)',
      tickfont: { size: 11 },
      automargin: true
    }, 
    yaxis: { 
      title: 'Flights',
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)',
      tickfont: { size: 11 }
    },
    bargap: 0.15,
    height: 400
  };
  layout.images = [{ source: '/static/logo.png', xref: 'paper', yref: 'paper', x: 1, y: 0, xanchor: 'right', yanchor: 'bottom', sizex: 0.15, sizey: 0.15, opacity: 0.85 }];
  const chartDiv = document.getElementById('chart-hourly');
  if (chartDiv.data) {
    Plotly.react('chart-hourly', data, layout, {responsive: true, displayModeBar: false});
  } else {
    Plotly.newPlot('chart-hourly', data, layout, {responsive: true, displayModeBar: false});
  }
}

function buildAirlineChart(flights) {
  if (!document.getElementById('chart-airline')) return;
  const stats = {};
  flights.forEach(f => {
    const name = (f.Airline || 'Unknown').split(' ')[0];
    if (!stats[name]) stats[name] = { total:0, ontime:0 };
    stats[name].total += 1;
    // Count "Landed", "Scheduled", "Arriving", or "Departing" as on-time
    const status = (f.Status || '').toLowerCase();
    if (status.includes('landed') || status.includes('scheduled') || 
        status.includes('arriving') || status.includes('departing') || 
        status.includes('track')) {
      stats[name].ontime += 1;
    }
  });
  // Sort by total flights and take top 10
  const sortedNames = Object.keys(stats).sort((a, b) => stats[b].total - stats[a].total).slice(0, 10);
  const vals = sortedNames.map(n => {
    const pct = (stats[n].ontime / stats[n].total) * 100;
    return Math.round(pct * 10) / 10; // Round to 1 decimal
  });
  const data = [{ x: sortedNames, y: vals, type: 'bar', marker: {color: '#2ecc71'}, text: vals.map(v => v.toFixed(1) + '%'), textposition: 'outside' }];
  const layout = { title: 'On-Time % by Airline (top 10)', margin: { t: 40 }, yaxis: { title: '%', range: [0, 105] } };
  layout.images = [{ source: '/static/logo.png', xref: 'paper', yref: 'paper', x: 1, y: 0, xanchor: 'right', yanchor: 'bottom', sizex: 0.15, sizey: 0.15, opacity: 0.85 }];
  const chartDiv = document.getElementById('chart-airline');
  if (chartDiv.data) {
    Plotly.react('chart-airline', data, layout, {responsive: true, displayModeBar: false});
  } else {
    Plotly.newPlot('chart-airline', data, layout, {responsive: true, displayModeBar: false});
  }
}

function buildMapChart(flights) {
  if (!document.getElementById('chart-map')) return;
  // Build a clean scattermapbox map centered on ICT
  const lats = [];
  const lons = [];
  const texts = [];
  const colors = [];
  
  flights.forEach(f => {
    const lat = f.latitude || f.Latitude;
    const lon = f.longitude || f.Longitude;
    if (lat && lon) {
      lats.push(lat);
      lons.push(lon);
      const flightNum = f.Flight_Number || 'N/A';
      const airline = f.Airline || '';
      const altitude = f.altitude || 0;
      const status = f.Status || '';
      const heading = f.heading || f.Heading || 0;
      const label = `<b>${flightNum}</b><br>${airline}<br>${altitude} ft<br>${status}<br>Heading: ${heading}°`;
      texts.push(label);
      // All planes as black
      colors.push('#000000');
    }
  });
  
  // Get current map state if it exists (to preserve zoom/pan on refresh)
  const mapDiv = document.getElementById('chart-map');
  let currentCenter = { lat: 39.0, lon: -98.0 };  // Center on continental US
  let currentZoom = 3.2;  // Zoom level to show full CONUS
  
  if (mapDiv && mapDiv.layout && mapDiv.layout.mapbox) {
    currentCenter = mapDiv.layout.mapbox.center || currentCenter;
    currentZoom = mapDiv.layout.mapbox.zoom || currentZoom;
  }
  
  const data = [
    {
      type: 'scattermapbox',
      mode: 'markers',
      lat: lats,
      lon: lons,
      text: texts,
      hovertemplate: '%{text}<extra></extra>',
      marker: { 
        size: 12, 
        color: colors,
        opacity: 0.9
      },
      name: 'Aircraft'
    },
    {
      type: 'scattermapbox',
      mode: 'markers+text',
      lat: [37.65],
      lon: [-97.43],
      text: ['ICT'],
      textfont: { size: 11, color: 'white', family: 'Arial Black' },
      textposition: 'middle center',
      hovertemplate: '<b>Wichita Dwight D. Eisenhower</b><br>National Airport (ICT)<br>37.65°N, 97.43°W<extra></extra>',
      marker: { 
        size: 16, 
        color: '#86BC25',
        symbol: 'circle',
        line: { width: 3, color: '#000000' }
      },
      name: 'ICT Airport'
    }
  ];
  
  const layout = { 
    title: {
      text: `Live Aircraft Tracking (${lats.length} flights)`,
      font: { size: 16, color: '#2C2C2C', family: 'Arial' }
    },
    mapbox: {
      style: 'open-street-map',
      center: currentCenter,
      zoom: currentZoom
    },
    margin: { t: 50, b: 20, l: 20, r: 20 },
    showlegend: false,
    paper_bgcolor: 'white',
    plot_bgcolor: 'white',
    font: { family: 'Arial' },
    uirevision: 'map-view'  // This preserves the map view on updates
  };
  
  const config = {
    responsive: true, 
    displayModeBar: false,
    scrollZoom: true
  };
  
  Plotly.react('chart-map', data, layout, config);
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

function updateCurrentTime() {
  const now = new Date();
  const currentTimeEl = document.getElementById('current-time');
  if (currentTimeEl) currentTimeEl.textContent = now.toLocaleTimeString();
}

function hasSignificantChange(newFlights, oldFlights) {
  if (!oldFlights) return true;
  if (newFlights.length !== oldFlights.length) return true;
  
  // Check if flight statuses changed significantly (more than 2 flights)
  let statusChanges = 0;
  const oldMap = new Map(oldFlights.map(f => [f.Flight_Number, f.Status]));
  
  for (const flight of newFlights) {
    const oldStatus = oldMap.get(flight.Flight_Number);
    if (oldStatus !== flight.Status) {
      statusChanges++;
      if (statusChanges > 2) return true;
    }
  }
  
  return false;
}

function startAutoRefresh() {
  let refreshInterval;
  
  function scheduleRefresh() {
    // Only refresh if page is visible
    if (document.hidden) {
      return;
    }
    fetchData();
  }
  
  // Start regular refresh
  refreshInterval = setInterval(scheduleRefresh, REFRESH_MS);
  
  // Pause/resume on visibility change
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      // Tab became visible - refresh immediately
      fetchData();
    }
  });
}

function startClock() {
  updateCurrentTime();
  setInterval(updateCurrentTime, 1000); // Update every second
}

function renderOperationsLog(data) {
  const summaryEl = document.getElementById('operations-summary');
  const listEl = document.getElementById('operations-list');
  if (!summaryEl || !listEl) return;
  
  if (!data || !data.summary) {
    summaryEl.innerHTML = '<div class="no-operations">No operations data available</div>';
    listEl.innerHTML = '';
    return;
  }
  
  const summary = data.summary;
  const operations = data.operations || [];
  
  // Render summary
  const totalOps = summary.total_operations || 0;
  const successCount = summary.by_status?.success || 0;
  const warningCount = summary.by_status?.warning || 0;
  const errorCount = summary.by_status?.error || 0;
  const infoCount = summary.by_status?.info || 0;
  
  summaryEl.innerHTML = `
    <h4>Today's Activity</h4>
    <div class="ops-stats">
      <div class="ops-stat">
        <div class="ops-stat-label">Total Ops</div>
        <div class="ops-stat-value">${totalOps}</div>
      </div>
      <div class="ops-stat">
        <div class="ops-stat-label">Success Rate</div>
        <div class="ops-stat-value">${totalOps > 0 ? Math.round((successCount / totalOps) * 100) : 0}%</div>
      </div>
    </div>
    <div class="ops-status-indicators">
      ${successCount > 0 ? `<span class="ops-status-indicator"><span class="status-dot success"></span>${successCount} Success</span>` : ''}
      ${infoCount > 0 ? `<span class="ops-status-indicator"><span class="status-dot info"></span>${infoCount} Info</span>` : ''}
      ${warningCount > 0 ? `<span class="ops-status-indicator"><span class="status-dot warning"></span>${warningCount} Warning</span>` : ''}
      ${errorCount > 0 ? `<span class="ops-status-indicator"><span class="status-dot error"></span>${errorCount} Error</span>` : ''}
    </div>
  `;
  
  // Render operations list (most recent first)
  if (operations.length === 0) {
    listEl.innerHTML = '<div class="no-operations">No operations logged today</div>';
    return;
  }
  
  // Show most recent 20 operations
  const recentOps = operations.slice(-20).reverse();
  
  const opsHtml = recentOps.map(op => {
    const categoryClass = `category-${op.category.toLowerCase().replace(/\s+/g, '-')}`;
    const statusClass = op.status || 'info';
    
    return `
      <div class="operation-item">
        <div class="operation-header">
          <span class="operation-time">${op.time || ''}</span>
          <span class="operation-category ${categoryClass}">${op.category || 'General'}</span>
        </div>
        <div class="operation-text">
          <span class="operation-status ${statusClass}"></span>
          ${op.operation || 'Operation'}
        </div>
        ${op.details ? `<div class="operation-details">${op.details}</div>` : ''}
      </div>
    `;
  }).join('');
  
  listEl.innerHTML = opsHtml;
}

window.addEventListener('load', () => {
  console.log('Page loaded');
  console.log('Plotly available:', typeof Plotly !== 'undefined');
  setupButtons();
  fetchData();
  startAutoRefresh();
  startClock();
});
