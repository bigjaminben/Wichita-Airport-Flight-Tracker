import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np
import seaborn as sns
import os
import csv
import requests
from bs4 import BeautifulSoup
import logging

# Module logger
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Set the style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("Set2")

# Global matplotlib settings for professional appearance
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 11
plt.rcParams['figure.titlesize'] = 16
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['grid.alpha'] = 0.3

# Enable interactive mode so plots update without blocking when run interactively
plt.ion()

class AirportFlightTrackerWithGraphs:
    def __init__(self, flights_file, weather_file):
        self.flights_file = flights_file
        self.weather_file = weather_file
        self.flights_data = []
        self.weather_data = {}
        self.create_sample_data_if_missing()
        self.load_data()
    
    def create_sample_data_if_missing(self):
        """Fetch live data from OpenSky (flights) and Open-Meteo (weather).
        
        Note: This method no longer creates hardcoded sample data files.
        If live fetch fails, empty lists are used gracefully.
        """
        logger.debug("Fetching live flights from OpenSky Network...")
        # Try to fetch live flight data from OpenSky
        self.flights_data = self._fetch_live_flights()
        logger.debug(f"Flights data after fetch: {len(self.flights_data)} flights")
        if self.flights_data:
            logger.debug(f"First flight: {self.flights_data[0].get('Flight_Number')}")
        
        logger.debug("Fetching live weather from Open-Meteo...")
        # Try to fetch live weather data from Open-Meteo
        self._fetch_live_weather()
        logger.debug(f"Weather data after fetch: {len(self.weather_data)} airports")
    
    def _fetch_live_flights(self):
        """Fetch live flights from OpenSky Network API for Wichita area.
        
        OpenSky Network provides free real-time flight data.
        Returns flights in the Wichita region.
        """
        # Wichita area bounding box (latitude, longitude)
        # lat_min, lon_min, lat_max, lon_max
        wichita_bbox = (37.45, -97.57, 38.05, -97.17)
        
        try:
            # OpenSky Network API endpoint (free tier, no auth required)
            url = "https://opensky-network.org/api/states/all"
            params = {
                'lamin': wichita_bbox[0],
                'lomin': wichita_bbox[1],
                'lamax': wichita_bbox[2],
                'lomax': wichita_bbox[3]
            }
            
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            flights_list = []
            if data.get('states'):
                for state in data['states']:
                    # Parse OpenSky state vector
                    flight_dict = {
                        'Flight_Number': state[1] if state[1] else 'N/A',  # callsign
                        'Origin': state[2] if state[2] else 'N/A',  # origin country
                        'Type': 'Arrival' if state[14] == 1 else 'Departure',  # on ground
                        'Airline': 'OpenSky Flight',
                        'Destination': 'ICT',
                        'Scheduled_Time': 'N/A',
                        'Actual_Time': 'N/A',
                        'Status': 'In Flight',
                        'Gate': 'N/A',
                        'Runway': 'N/A',
                        'Aircraft_Type': 'Aircraft',
                        'Latitude': state[6],
                        'Longitude': state[5],
                        'Altitude': state[7],
                        'Velocity': state[9]
                    }
                    flights_list.append(flight_dict)
            
            logger.info(f"Fetched {len(flights_list)} live flights from OpenSky Network for Wichita area")
            return flights_list
        except Exception as e:
            logger.warning(f"Could not fetch flights from OpenSky Network: {e}")
        
        logger.warning("No flight data available - showing empty dashboard")
        return []
    
    def _fetch_live_weather(self):
        """Fetch live weather data from Open-Meteo API for major airports."""
        # Define airports with their coordinates
        airports = {
            'ICT': {'name': 'Wichita', 'lat': 37.75, 'lon': -97.37},
            'DFW': {'name': 'Dallas', 'lat': 32.90, 'lon': -97.04},
            'DEN': {'name': 'Denver', 'lat': 39.86, 'lon': -104.67},
            'ATL': {'name': 'Atlanta', 'lat': 33.64, 'lon': -84.43},
            'PHX': {'name': 'Phoenix', 'lat': 33.43, 'lon': -112.01},
            'ORD': {'name': 'Chicago', 'lat': 41.98, 'lon': -87.90},
            'IAH': {'name': 'Houston', 'lat': 29.98, 'lon': -95.34},
            'MSP': {'name': 'Minneapolis', 'lat': 44.88, 'lon': -93.22},
        }
        
        for code, info in airports.items():
            try:
                # Enhanced API call with precipitation and more data
                url = (
                    f"https://api.open-meteo.com/v1/forecast"
                    f"?latitude={info['lat']}&longitude={info['lon']}"
                    f"&current=temperature_2m,relative_humidity_2m,weathercode,windspeed_10m,visibility,precipitation,precipitation_probability"
                    f"&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch&timezone=auto"
                )
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                data = r.json()
                
                if 'current' in data:
                    current = data['current']
                    # Map weather codes to conditions
                    weather_code = current.get('weathercode', 0)
                    conditions = {
                        0: 'Clear', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Overcast',
                        45: 'Foggy', 48: 'Foggy', 51: 'Light Drizzle', 53: 'Drizzle', 55: 'Heavy Drizzle',
                        61: 'Light Rain', 63: 'Rain', 65: 'Heavy Rain', 71: 'Light Snow', 73: 'Snow', 75: 'Heavy Snow',
                        80: 'Light Showers', 81: 'Showers', 82: 'Heavy Showers', 95: 'Thunderstorm'
                    }
                    condition = conditions.get(weather_code, 'Unknown')
                    
                    # Visibility conversion: meters to miles (if available)
                    visibility_m = current.get('visibility', 10000)  # default 10km
                    visibility_miles = round(visibility_m * 0.000621371, 1)
                    
                    self.weather_data[code] = {
                        'Airport_Code': code,
                        'City': info['name'],
                        'Temperature_F': int(current.get('temperature_2m', 70)),
                        'Condition': condition,
                        'Wind_Speed_mph': int(current.get('windspeed_10m', 0)),
                        'Visibility_miles': visibility_miles,
                        'Humidity_percent': int(current.get('relative_humidity_2m', 50)),
                        'Precipitation_inches': round(current.get('precipitation', 0.0), 2),
                        'Precipitation_probability': int(current.get('precipitation_probability', 0)),
                        'weathercode': weather_code
                    }
            except Exception as e:
                logger.warning(f"Could not fetch weather for {code}: {e}")
        
        if self.weather_data:
            logger.info(f"Fetched live weather for {len(self.weather_data)} airports")
            # Log operation
            try:
                from operations_logger import log_data_fetch
                log_data_fetch(f"Weather data fetched for {len(self.weather_data)} airports", "success")
            except:
                pass
        else:
            logger.warning("No weather data available")
    
    def load_data(self):
        """Load flight and weather data from live sources or empty gracefully."""
        try:
            # Data is already loaded by create_sample_data_if_missing()
            # which now fetches live data instead of creating files
            
            logger.debug(f"In load_data(): flights_data has {len(self.flights_data)} items")
            logger.debug(f"In load_data(): weather_data has {len(self.weather_data)} items")
            
            if self.flights_data and self.weather_data:
                logger.info(f"OK - Loaded {len(self.flights_data)} flights and weather for {len(self.weather_data)} airports")
            elif self.flights_data:
                logger.info(f"OK - Loaded {len(self.flights_data)} flights (no weather data)")
            elif self.weather_data:
                logger.info(f"OK - Loaded weather for {len(self.weather_data)} airports (no flight data)")
            else:
                logger.warning("No live data available. All visualizations will be empty.")
            
        except Exception as e:
            logger.error(f"ERROR loading data: {e}", exc_info=True)
    
    def plot_flight_status_pie_chart(self):
        """Create a professional pie chart of flight statuses"""
        if not self.flights_data:
            logger.warning("No flight data available for pie chart")
            return
            
        status_counts = Counter(flight.get('Status', 'Unknown') for flight in self.flights_data)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Professional color scheme
        colors = ['#2ecc71', '#f39c12', '#e74c3c', '#3498db']
        
        wedges, texts, autotexts = ax.pie(
            status_counts.values(), 
            labels=status_counts.keys(),
            autopct='%1.1f%%',
            colors=colors[:len(status_counts)],
            explode=[0.05] * len(status_counts),
            shadow=True,
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        
        # Enhance text appearance
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(13)
        
        for text in texts:
            text.set_fontsize(12)
            text.set_weight('bold')
        
        ax.set_title('Flight Status Distribution\nWichita Airport (ICT)', 
                    fontsize=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.show()
    
    def plot_airline_performance_bar_chart(self):
        """Create a professional bar chart showing airline performance"""
        if not self.flights_data:
            logger.warning("No flight data available for airline chart")
            return
            
        airline_stats = defaultdict(lambda: {'total': 0, 'in_flight': 0})
        
        for flight in self.flights_data:
            airline = flight.get('Airline', 'Unknown').replace(' Flight', '')[:15]
            airline_stats[airline]['total'] += 1
            if flight.get('Status') == 'In Flight':
                airline_stats[airline]['in_flight'] += 1
        
        airlines = list(airline_stats.keys())
        in_flight = [airline_stats[airline]['in_flight'] for airline in airlines]
        total = [airline_stats[airline]['total'] for airline in airlines]
        
        fig, ax = plt.subplots(figsize=(13, 7))
        
        x = np.arange(len(airlines))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, in_flight, width, label='In Flight', 
                      color='#3498db', alpha=0.85, edgecolor='black', linewidth=1.2)
        bars2 = ax.bar(x + width/2, total, width, label='Total', 
                      color='#2ecc71', alpha=0.85, edgecolor='black', linewidth=1.2)
        
        ax.set_xlabel('Airlines', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Flights', fontsize=12, fontweight='bold')
        ax.set_title('Airline Flight Activity\nWichita Airport (ICT)', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(airlines, rotation=45, ha='right', fontweight='bold')
        ax.legend(fontsize=11, loc='upper right', framealpha=0.95)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                           f'{int(height)}', ha='center', va='bottom', 
                           fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        plt.show()
    
    def plot_hourly_flight_activity(self):
        """Create a professional line chart showing flight activity by hour"""
        if not self.flights_data:
            logger.warning("No flight data available for hourly chart")
            return
        
        hourly_activity = defaultdict(int)
        
        for flight in self.flights_data:
            # For live data, we'll just use the current hour for demo
            from datetime import datetime
            current_hour = datetime.now().hour
            hourly_activity[current_hour] += 1
        
        if not hourly_activity:
            logger.warning("No hourly data available")
            return
        
        hours = sorted(hourly_activity.keys())
        activity = [hourly_activity[hour] for hour in hours]
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Create area plot
        ax.fill_between(hours, activity, alpha=0.4, color='#3498db', label='Flight Activity')
        ax.plot(hours, activity, marker='o', linewidth=3, markersize=10, 
               color='#2980b9', label='Live Activity', markeredgecolor='white', markeredgewidth=2)
        
        ax.set_xlabel('Hour of Day (UTC)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Flights', fontsize=12, fontweight='bold')
        ax.set_title('Real-Time Flight Activity\nWichita Airport (ICT)', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.legend(fontsize=11, loc='upper left', framealpha=0.95)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xticks(range(0, 24, 2))
        
        # Add value labels
        for hour, count in zip(hours, activity):
            ax.text(hour, count + 0.2, f'{int(count)}', ha='center', va='bottom', 
                   fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        plt.show()
    
    def plot_weather_comparison(self):
        """Create a professional multi-subplot weather comparison"""
        if not self.weather_data:
            logger.warning("No weather data available for plotting")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Weather Conditions at Connected Airports', fontsize=18, fontweight='bold', y=0.995)
        
        cities = [data['City'] for data in self.weather_data.values()]
        temps = [int(data['Temperature_F']) for data in self.weather_data.values()]
        wind_speeds = [int(data['Wind_Speed_mph']) for data in self.weather_data.values()]
        visibility = [int(data['Visibility_miles']) for data in self.weather_data.values()]
        humidity = [int(data['Humidity_percent']) for data in self.weather_data.values()]
     
        # Temperature bar chart with color gradient
        colors_temp = ['#e74c3c' if t > 85 else '#f39c12' if t > 70 else '#3498db' for t in temps]
        bars1 = ax1.bar(cities, temps, color=colors_temp, alpha=0.85, edgecolor='black', linewidth=1.2)
        ax1.set_title('Temperature (°F)', fontweight='bold', fontsize=13, pad=10)
        ax1.set_ylabel('Temperature (°F)', fontweight='bold', fontsize=11)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add temperature values on bars
        for bar, temp in zip(bars1, temps):
            ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                    f'{temp}°F', ha='center', va='bottom', fontweight='bold', fontsize=10)

        # Wind speed bar chart
        bars2 = ax2.bar(cities, wind_speeds, color='#3498db', alpha=0.85, edgecolor='black', linewidth=1.2)
        ax2.set_title('Wind Speed (mph)', fontweight='bold', fontsize=13, pad=10)
        ax2.set_ylabel('Wind Speed (mph)', fontweight='bold', fontsize=11)
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(axis='y', alpha=0.3, linestyle='--')

        # Add wind speed values on bars
        for bar, wind in zip(bars2, wind_speeds):
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.3,
                    f'{wind}mph', ha='center', va='bottom', fontweight='bold', fontsize=10)

        # Visibility bar chart
        bars3 = ax3.bar(cities, visibility, color='#2ecc71', alpha=0.85, edgecolor='black', linewidth=1.2)
        ax3.set_title('Visibility (miles)', fontweight='bold', fontsize=13, pad=10)
        ax3.set_ylabel('Visibility (miles)', fontweight='bold', fontsize=11)
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(axis='y', alpha=0.3, linestyle='--')

        # Add visibility values on bars
        for bar, vis in zip(bars3, visibility):
            ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.2,
                    f'{vis}mi', ha='center', va='bottom', fontweight='bold', fontsize=10)

        # Humidity bar chart
        bars4 = ax4.bar(cities, humidity, color='#9b59b6', alpha=0.85, edgecolor='black', linewidth=1.2)
        ax4.set_title('Humidity (%)', fontweight='bold', fontsize=13, pad=10)
        ax4.set_ylabel('Humidity (%)', fontweight='bold', fontsize=11)
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(axis='y', alpha=0.3, linestyle='--')
        ax4.set_ylim(0, 100)
        
        # Add humidity values on bars
        for bar, hum in zip(bars4, humidity):
            ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                    f'{hum}%', ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        plt.show()
    
    def plot_runway_utilization(self):
        """Create a professional donut chart showing runway utilization"""
        if not self.flights_data:
            logger.warning("No flight data available")
            return
        
        runway_usage = defaultdict(int)
        
        for flight in self.flights_data:
            if flight['Runway'] != 'N/A' and flight['Status'] != 'Cancelled':
                runway_usage[flight['Runway']] += 1
        
        if not runway_usage:
            logger.warning("No runway data available for plotting")
            return
        
        fig, ax = plt.subplots(figsize=(11, 9))
        
        # Professional color palette
        colors = ['#3498db', '#e67e22', '#2ecc71', '#e74c3c', '#9b59b6', '#1abc9c']
        
        # Create donut chart with enhanced styling
        runway_labels = [f"Runway {runway}" for runway in runway_usage.keys()]
        wedges, texts, autotexts = ax.pie(runway_usage.values(), 
                                          labels=runway_labels,
                                          autopct='%1.1f%%',
                                          colors=colors[:len(runway_usage)],
                                          pctdistance=0.85,
                                          wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
                                          startangle=90,
                                          textprops={'fontsize': 11, 'fontweight': 'bold'})
        
        # Enhance autotext (percentages)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        # Draw center circle for donut effect
        centre_circle = plt.Circle((0, 0), 0.70, fc='white', edgecolor='#ecf0f1', linewidth=2)
        ax.add_artist(centre_circle)
        
        ax.set_title('Runway Utilization\nWichita Airport (ICT)', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Add total flights in center
        total_flights = sum(runway_usage.values())
        plt.text(0, 0, f'Total\nFlights\n{total_flights}', 
                horizontalalignment='center', verticalalignment='center',
                fontsize=14, fontweight='bold', color='#2c3e50')
        
        ax.axis('equal')
        plt.tight_layout()
        plt.show()
    
    def plot_delay_analysis(self):
        """Create a professional scatter plot analyzing delays"""
        if not self.flights_data:
            logger.warning("No flight data available")
            return
            
        scheduled_times = []
        delay_minutes = []
        airlines = []
        colors_map = {'American': '#e74c3c', 'United': '#3498db', 'Delta': '#2ecc71', 'Southwest': '#f39c12'}
        
        for flight in self.flights_data:
            if (flight['Status'] == 'Delayed' and 
                flight['Scheduled_Time'] != 'N/A' and 
                flight['Actual_Time'] != 'N/A'):
                
                try:
                    # Parse times
                    scheduled = datetime.strptime(flight['Scheduled_Time'], '%H:%M')
                    actual = datetime.strptime(flight['Actual_Time'], '%H:%M')
                    
                    # Calculate delay in minutes
                    delay = (actual - scheduled).total_seconds() / 60
                    
                    if delay > 0:  # Only positive delays
                        scheduled_times.append(scheduled.hour + scheduled.minute/60)
                        delay_minutes.append(delay)
                        
                        # Get airline color
                        airline_key = flight['Airline'].split()[0]  # First word of airline name
                        airlines.append(colors_map.get(airline_key, '#95a5a6'))
                
                except:
                    continue
        
        if not delay_minutes:
            logger.warning("No delay data available for plotting")
            return
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create scatter plot with enhanced styling
        scatter = ax.scatter(scheduled_times, delay_minutes, 
                            c=airlines, s=150, alpha=0.75, edgecolors='black', 
                            linewidth=1.5, zorder=3)
        
        ax.set_xlabel('Scheduled Time (Hour of Day)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Delay (Minutes)', fontsize=12, fontweight='bold')
        ax.set_title('Flight Delays Analysis\nWichita Airport (ICT)', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
        ax.set_axisbelow(True)
        
        # Add trend line with professional styling
        if len(scheduled_times) > 1:
            z = np.polyfit(scheduled_times, delay_minutes, 1)
            p = np.poly1d(z)
            x_trend = np.linspace(min(scheduled_times), max(scheduled_times), 100)
            ax.plot(x_trend, p(x_trend), color='#e74c3c', linestyle='--', 
                   alpha=0.8, linewidth=2.5, label='Trend Line', zorder=2)
        
        # Add average delay line
        avg_delay = np.mean(delay_minutes)
        ax.axhline(y=avg_delay, color='#f39c12', linestyle=':', linewidth=2.5, 
                   label=f'Average Delay: {avg_delay:.1f} min', alpha=0.9, zorder=1)
        
        ax.legend(fontsize=11, loc='upper left', framealpha=0.95)
        
        plt.tight_layout()
        plt.show()
    
    def plot_comprehensive_dashboard(self):
        """Create a professional comprehensive dashboard with multiple charts"""
        if not self.flights_data:
            logger.warning("No flight data available")
            return
        
        fig = plt.figure(figsize=(20, 12))
        fig.suptitle('Wichita Airport (ICT) - Comprehensive Flight Dashboard', 
                    fontsize=20, fontweight='bold', y=0.98)
        fig.patch.set_facecolor('#f8f9fa')
        
        # 1. Flight Status Pie Chart (top left)
        ax1 = plt.subplot(2, 3, 1)
        status_counts = Counter(flight['Status'] for flight in self.flights_data)
        colors_status = {'On Time': '#2ecc71', 'Delayed': '#f39c12', 'Cancelled': '#e74c3c'}
        colors = [colors_status.get(s, '#95a5a6') for s in status_counts.keys()]
        wedges, texts, autotexts = ax1.pie(status_counts.values(), labels=status_counts.keys(), 
                                           autopct='%1.1f%%', colors=colors, startangle=90,
                                           wedgeprops=dict(edgecolor='white', linewidth=2))
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        ax1.set_title('Flight Status Distribution', fontweight='bold', fontsize=12, pad=10)
        
        # 2. Hourly Activity (top middle)
        ax2 = plt.subplot(2, 3, 2)
        hourly_activity = defaultdict(int)
        for flight in self.flights_data:
            if flight['Scheduled_Time'] != 'N/A' and flight['Status'] != 'Cancelled':
                try:
                    hour = int(flight['Scheduled_Time'].split(':')[0])
                    hourly_activity[hour] += 1
                except:
                    continue
        
        if hourly_activity:
            hours = sorted(hourly_activity.keys())
            activity = [hourly_activity[hour] for hour in hours]
            ax2.fill_between(hours, activity, alpha=0.4, color='#3498db')
            ax2.plot(hours, activity, marker='o', linewidth=2.5, markersize=8, 
                    color='#2980b9', markeredgecolor='white', markeredgewidth=1.5)
            ax2.set_title('Hourly Flight Activity', fontweight='bold', fontsize=12, pad=10)
            ax2.set_xlabel('Hour of Day', fontsize=10, fontweight='bold')
            ax2.set_ylabel('Number of Flights', fontsize=10, fontweight='bold')
            ax2.grid(True, alpha=0.3, linestyle='--')
        
        # 3. Airline Performance (top right)
        ax3 = plt.subplot(2, 3, 3)
        airline_stats = defaultdict(lambda: {'total': 0, 'on_time': 0})
        for flight in self.flights_data:
            airline = flight['Airline'].replace(' Airlines', '').replace(' ', '')[:8]
            airline_stats[airline]['total'] += 1
            if flight['Status'] == 'On Time':
                airline_stats[airline]['on_time'] += 1
        
        if airline_stats:
            airlines = list(airline_stats.keys())
            on_time_pct = [(airline_stats[airline]['on_time'] / airline_stats[airline]['total']) * 100 
                          for airline in airlines]
            
            bars = ax3.bar(airlines, on_time_pct, color='#2ecc71', alpha=0.85, 
                          edgecolor='black', linewidth=1.2)
            ax3.set_title('On-Time Performance by Airline', fontweight='bold', fontsize=12, pad=10)
            ax3.set_ylabel('On-Time Percentage (%)', fontsize=10, fontweight='bold')
            ax3.tick_params(axis='x', rotation=45)
            ax3.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Add percentage labels on bars
            for bar, pct in zip(bars, on_time_pct):
                ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                        f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        # 4. Temperature Comparison (bottom left)
        ax4 = plt.subplot(2, 3, 4)
        if self.weather_data:
            cities = [data['City'] for data in self.weather_data.values()]
            temps = [int(data['Temperature_F']) for data in self.weather_data.values()]
            colors_temp = ['#e74c3c' if t > 85 else '#f39c12' if t > 70 else '#3498db' for t in temps]
            bars = ax4.bar(cities, temps, color=colors_temp, alpha=0.85, 
                          edgecolor='black', linewidth=1.2)
            ax4.set_title('Temperature at Connected Airports', fontweight='bold', fontsize=12, pad=10)
            ax4.set_ylabel('Temperature (°F)', fontsize=10, fontweight='bold')
            ax4.tick_params(axis='x', rotation=45)
            ax4.grid(axis='y', alpha=0.3, linestyle='--')
            for bar, temp in zip(bars, temps):
                ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                        f'{temp}F', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        # 5. Aircraft Types (bottom middle)
        ax5 = plt.subplot(2, 3, 5)
        aircraft_counts = Counter(flight['Aircraft_Type'] for flight in self.flights_data 
                                if flight['Aircraft_Type'] != 'N/A')
        if aircraft_counts:
            wedges, texts, autotexts = ax5.pie(aircraft_counts.values(), 
                                               labels=aircraft_counts.keys(), 
                                               autopct='%1.1f%%', startangle=90,
                                               colors=['#3498db', '#e67e22', '#2ecc71', '#e74c3c'],
                                               wedgeprops=dict(edgecolor='white', linewidth=2))
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)
            ax5.set_title('Aircraft Types Distribution', fontweight='bold', fontsize=12, pad=10)
        
        # 6. Runway Usage (bottom right)
        ax6 = plt.subplot(2, 3, 6)
        runway_usage = Counter(flight['Runway'] for flight in self.flights_data 
                             if flight['Runway'] != 'N/A' and flight['Status'] != 'Cancelled')
        if runway_usage:
            runways = list(runway_usage.keys())
            usage = list(runway_usage.values())
            bars = ax6.bar(runways, usage, color=['#3498db', '#e67e22', '#2ecc71', '#e74c3c'][:len(runway_usage)], 
                          alpha=0.85, edgecolor='black', linewidth=1.2)
            ax6.set_title('Runway Utilization', fontweight='bold', fontsize=12, pad=10)
            ax6.set_ylabel('Number of Flights', fontsize=10, fontweight='bold')
            ax6.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Add value labels on bars
            for bar, val in zip(bars, usage):
                ax6.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                        f'{val}', ha='center', va='bottom', fontweight='bold', fontsize=10)
            
            # Add value labels on bars
            for bar, val in zip(bars, usage):
                plt.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                        f'{val}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.show()
    
    def run_visualization_menu(self):
        """Run an interactive visualization menu"""
        while True:
            print("\n" + "="*60)
            print("AIRPORT FLIGHT TRACKER - VISUALIZATION MENU")
            print("="*60)
            print("1. Flight Status Pie Chart")
            print("2. Airline Performance Bar Chart")
            print("3. Hourly Flight Activity Line Chart")
            print("4. Weather Comparison Charts")
            print("5. Runway Utilization Donut Chart")
            print("6. Flight Delays Scatter Plot")
            print("7. Comprehensive Dashboard (All Charts)")
            print("8. Back to Main Menu")
            print("="*60)
            
            choice = input("Enter your choice (1-8): ").strip()
            
            if choice == '1':
                self.plot_flight_status_pie_chart()
            elif choice == '2':
                self.plot_airline_performance_bar_chart()
            elif choice == '3':
                self.plot_hourly_flight_activity()
            elif choice == '4':
                self.plot_weather_comparison()
            elif choice == '5':
                self.plot_runway_utilization()
            elif choice == '6':
                self.plot_delay_analysis()

            elif choice == '7':
                self.plot_comprehensive_dashboard()
            elif choice == '8':
                break
            else:
                logger.warning("Invalid choice. Please enter 1-8.")
            
    
    def display_dashboard(self):
        """Display the main dashboard with statistics"""
        logger.info("\n" + "="*80)
        logger.info("WICHITA AIRPORT (ICT) - FLIGHT TRACKER DASHBOARD")
        logger.info("="*80)
        
        # Flight Statistics
        total_flights = len(self.flights_data)
        arrivals = len([f for f in self.flights_data if f.get('Type') == 'Arrival'])
        departures = len([f for f in self.flights_data if f.get('Type') == 'Departure'])
        on_time = len([f for f in self.flights_data if f.get('Status') == 'On Time'])
        delayed = len([f for f in self.flights_data if f.get('Status') == 'Delayed'])
        cancelled = len([f for f in self.flights_data if f.get('Status') == 'Cancelled'])
        
        logger.info(f"FLIGHT STATISTICS")
        logger.info(f"   Total Flights: {total_flights}")
        logger.info(f"   Arrivals: {arrivals} | Departures: {departures}")
        if total_flights > 0:
            logger.info(f"   [OK] On Time: {on_time} ({on_time/total_flights*100:.1f}%)")
            logger.info(f"   [DELAY] Delayed: {delayed} ({delayed/total_flights*100:.1f}%)")
            print(f"   [CANCEL] Cancelled: {cancelled} ({cancelled/total_flights*100:.1f}%)")
        else:
            print(f"   [No flight data available]")
        
        # Weather Summary
        if self.weather_data and 'ICT' in self.weather_data:
            weather = self.weather_data['ICT']
            print(f"\nCURRENT WEATHER - WICHITA")
            print(f"   Temperature: {weather.get('Temperature_F', 'N/A')}F")
            print(f"   Condition: {weather.get('Condition', 'N/A')}")
            print(f"   Wind: {weather.get('Wind_Speed_mph', 'N/A')} mph")
            print(f"   Visibility: {weather.get('Visibility_miles', 'N/A')} miles")
        
        # Airline Summary
        if total_flights > 0:
            airline_counts = Counter(f.get('Airline', 'Unknown') for f in self.flights_data)
            print(f"\nAIRLINES OPERATING TODAY")
            for airline, count in airline_counts.most_common(3):
                short_name = airline.replace(' Airlines', '')
                print(f"   {short_name}: {count} flights")
        
        print("="*80)
    
    def display_arrivals_board(self):
        """Display arrivals board"""
        arrivals = [flight for flight in self.flights_data if flight.get('Type') == 'Arrival']
        
        print(f"\nARRIVALS BOARD - {len(arrivals)} flights")
        print("="*100)
        print(f"{ 'Flight':<8} {'Airline':<18} {'From':<6} {'Scheduled':<10} {'Actual':<10} {'Status':<12} {'Gate':<6} {'Runway':<8}")
        print("-"*100)
        
        if len(arrivals) == 0:
            print("[No arrival flights data available]")
        else:
            for flight in arrivals:
                airline_short = flight.get('Airline', 'N/A').replace(' Airlines', '')[:17]
                
                # Status icons (ASCII)
                status = flight.get('Status', 'Unknown')
                status_icon = "[OK]" if status == 'On Time' else "[DELAY]" if status == 'Delayed' else "[CANCEL]"
                
                print(f"{flight.get('Flight_Number', 'N/A'):<8} {airline_short:<18} {flight.get('Origin', 'N/A'):<6} {flight.get('Scheduled_Time', 'N/A'):<10} {flight.get('Actual_Time', 'N/A'):<10} {status_icon} {status:<10} {flight.get('Gate', 'N/A'):<6} {flight.get('Runway', 'N/A'):<8}")
                
                if flight.get('Origin') in self.weather_data:
                    weather = self.weather_data[flight.get('Origin')]
                    logger.info(f"         Weather at {flight.get('Origin')}: {weather.get('Temperature_F')}F, {weather.get('Condition')}")
                    logger.info("")
    
    def display_departures_board(self):
        """Display departures board"""
        departures = [flight for flight in self.flights_data if flight.get('Type') == 'Departure']
        
        print(f"\nDEPARTURES BOARD - {len(departures)} flights")
        print("="*100)
        print(f"{ 'Flight':<8} {'Airline':<18} {'To':<6} {'Scheduled':<10} {'Actual':<10} {'Status':<12} {'Gate':<6} {'Runway':<8}")
        print("-"*100)
        
        if len(departures) == 0:
            print("[No departure flights data available]")
        else:
            for flight in departures:
                airline_short = flight.get('Airline', 'N/A').replace(' Airlines', '')[:17]
                
                # Status icons (ASCII)
                status = flight.get('Status', 'Unknown')
                status_icon = "[OK]" if status == 'On Time' else "[DELAY]" if status == 'Delayed' else "[CANCEL]"
                
                print(f"{flight.get('Flight_Number', 'N/A'):<8} {airline_short:<18} {flight.get('Destination', 'N/A'):<6} {flight.get('Scheduled_Time', 'N/A'):<10} {flight.get('Actual_Time', 'N/A'):<10} {status_icon} {status:<10} {flight.get('Gate', 'N/A'):<6} {flight.get('Runway', 'N/A'):<8}")
                
                if flight.get('Destination') in self.weather_data:
                    weather = self.weather_data[flight.get('Destination')]
                    logger.info(f"         Weather at {flight.get('Destination')}: {weather.get('Temperature_F')}F, {weather.get('Condition')}")
                    logger.info("")
    
    def display_delays_and_cancellations(self):
        """Display detailed information about delays and cancellations"""
        delayed_flights = [flight for flight in self.flights_data if flight.get('Status') == 'Delayed']
        cancelled_flights = [flight for flight in self.flights_data if flight.get('Status') == 'Cancelled']
        
        print(f"\n[DELAYS] DELAYED FLIGHTS ({len(delayed_flights)} total)")
        print("="*80)
        if delayed_flights:
            for flight in delayed_flights:
                print(f"Flight {flight.get('Flight_Number')} ({flight.get('Airline')})")
                print(f"  Route: {flight.get('Origin')} -> {flight.get('Destination')}")
                print(f"  Scheduled: {flight.get('Scheduled_Time')} | Actual: {flight.get('Actual_Time')}")
                print(f"  Gate: {flight.get('Gate')} | Runway: {flight.get('Runway')}")
                print("")
        else:
            print("No delayed flights at this time.")
        
        print(f"\n[CANCEL] CANCELLED FLIGHTS ({len(cancelled_flights)} total)")
        print("="*80)
        if cancelled_flights:
            for flight in cancelled_flights:
                print(f"Flight {flight.get('Flight_Number')} ({flight.get('Airline')})")
                print(f"  Route: {flight.get('Origin')} -> {flight.get('Destination')}")
                print(f"  Originally scheduled: {flight.get('Scheduled_Time')}")
                print("")
        else:
            print("No cancelled flights at this time.")
    
    def run_main_menu(self):
        """Run the main interactive menu system"""
        while True:
            print("\n" + "="*60)
            print("AIRPORT FLIGHT TRACKER - MAIN MENU")
            print("="*60)
            print("1. Main Dashboard")
            print("2. Arrivals Board")
            print("3. Departures Board")
            print("4. Delays & Cancellations")
            print("5. 📊 Data Visualizations")
            print("6. Exit")
            print("="*60)
            
            choice = input("Enter your choice (1-6): ").strip()
            
            if choice == '1':
                self.display_dashboard()
            elif choice == '2':
                self.display_arrivals_board()
            elif choice == '3':
                self.display_departures_board()
            elif choice == '4':
                self.display_delays_and_cancellations()
            elif choice == '5':
                self.run_visualization_menu()
            elif choice == '6':
                print("Thank you for using Airport Flight Tracker!")
                break
            else:
                logger.warning("Invalid choice. Please enter 1-6.")
            
            if choice != '5':  # Don't pause after visualization menu
                input("\nPress Enter to continue...")

# Installation check and requirements
def check_requirements():
    """Check if required packages are installed"""
    required_packages = ['matplotlib', 'seaborn', 'numpy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 To install missing packages, run:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

# Main execution
def main():
    """Main function to run the Airport Flight Tracker with Visualizations"""
    print("Starting Airport Flight Tracker with Data Visualizations...")
    print("="*70)
    
    # Check if required packages are installed
    if not check_requirements():
        print("\nPlease install the required packages and run again.")
        return
    
    print("OK - All required packages are installed!")
    print("NOTE - Data will be fetched from live sources (FlyWichita, Open-Meteo)")
    
    # Initialize the flight tracker
    tracker = AirportFlightTrackerWithGraphs('flights_data.txt', 'weather_data.txt')
    
    if tracker.weather_data:
        print("OK - Flight tracker initialized successfully!")
        
        # Show quick preview
        print(f"\nQuick Stats:")
        print(f"   - {len(tracker.flights_data)} flights loaded")
        print(f"   - {len(tracker.weather_data)} airports with weather data")
        
        # Run the main menu
        tracker.run_main_menu()
    else:
        print("ERROR - Failed to load weather data. Please check your internet connection.")

if __name__ == "__main__":
    main()
