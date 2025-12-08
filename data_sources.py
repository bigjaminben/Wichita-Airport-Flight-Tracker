"""
Enhanced data sources for Airport Tracker
Integrates multiple real-time and statistical data sources
Uses HDF5 for hierarchical storage and Redis for real-time caching
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from flight_history import FlightHistoryDB
from hdf5_storage import get_storage
from redis_cache import get_cache

logger = logging.getLogger(__name__)

class FlightDataAggregator:
    """Aggregates flight data from multiple sources with Redis caching"""
    
    def __init__(self):
        self.cache_timeout = 15  # seconds (Redis TTL is separate)
        self.last_fetch = {}
        self.cached_data = {}
        self.history_db = FlightHistoryDB()  # SQLite for legacy support
        self.hdf5_storage = get_storage()  # HDF5 for hierarchical storage
        self.redis_cache = get_cache()  # Redis for real-time caching
    
    @staticmethod
    def normalize_airport_code(text: str) -> str:
        """
        Normalize airport codes from various formats to clean 3-letter codes.
        Examples: 'DenverDEN' -> 'DEN', 'Dallas/Fort WorthDFW' -> 'DFW'
        """
        if not text:
            return text
        
        # Common airport codes - extract if found at end
        import re
        # Match 3-letter code at the end
        match = re.search(r'([A-Z]{3})$', text)
        if match:
            return match.group(1)
        
        # Already clean 3-letter code
        if len(text) == 3 and text.isupper():
            return text
        
        return text  # Return as-is if can't parse
    
    @staticmethod
    def _parse_flight_datetime(date_str: str, time_str: str) -> str:
        """
        Parse date and time strings into ISO 8601 datetime.
        
        Args:
            date_str: Date string (e.g., 'Dec 08', 'Today', 'Tomorrow')
            time_str: Time string (e.g., '05:38', '14:20')
        
        Returns:
            ISO 8601 datetime string with timezone (e.g., '2025-12-08T05:38:00-06:00')
        """
        from datetime import datetime, timedelta
        from dateutil import parser
        import pytz
        
        if not time_str or time_str == 'N/A':
            return 'N/A'
        
        try:
            # Handle relative dates
            today = datetime.now()
            if date_str.lower() == 'today':
                date_obj = today
            elif date_str.lower() == 'tomorrow':
                date_obj = today + timedelta(days=1)
            elif date_str.lower() == 'yesterday':
                date_obj = today - timedelta(days=1)
            else:
                # Parse date string (e.g., 'Dec 08')
                date_obj = parser.parse(f"{date_str} {today.year}")
                # If parsed date is more than 6 months in past, assume next year
                if (today - date_obj).days > 180:
                    date_obj = date_obj.replace(year=today.year + 1)
            
            # Parse time
            time_obj = parser.parse(time_str).time()
            
            # Combine date and time
            combined = datetime.combine(date_obj.date(), time_obj)
            
            # Add Central Time zone (ICT is in CST/CDT)
            central = pytz.timezone('America/Chicago')
            localized = central.localize(combined)
            
            return localized.isoformat()
        except Exception as e:
            logger.warning(f"Could not parse datetime '{date_str} {time_str}': {e}")
            return 'N/A'
        
    def fetch_flightradar24_data(self, bounds: tuple = (34.0, 41.0, -102.0, -92.0)) -> List[Dict]:
        """
        Fetch live flight data from Flightradar24 with Redis caching
        
        Args:
            bounds: (lat_min, lat_max, lon_min, lon_max) - Expanded to ~400 mile radius 
                    to capture all flights arriving to ICT (not just overhead)
        
        Returns:
            List of flight dictionaries filtered to ICT arrivals/departures
        """
        cache_key = 'flightradar24'
        
        # Try Redis cache first
        cached = self.redis_cache.get(cache_key)
        if cached:
            logger.info(f"Using Redis cached data for {cache_key}")
            return cached
        
        # Fall back to memory cache
        if self._is_cached(cache_key):
            return self.cached_data[cache_key]
        
        try:
            # Flightradar24 API endpoint
            url = "https://data-cloud.flightradar24.com/zones/fcgi/feed.js"
            params = {
                'bounds': f"{bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]}",
                'faa': '1',
                'satellite': '1',
                'mlat': '1',
                'flarm': '1',
                'adsb': '1',
                'gnd': '0',
                'air': '1',
                'vehicles': '0',
                'estimated': '1',
                'maxage': '14400',
                'gliders': '0',
                'stats': '1'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            flights = []
            
            # Parse Flightradar24 response
            for key, value in data.items():
                if isinstance(value, list) and len(value) >= 13:
                    origin = value[11] if len(value) > 11 else 'Unknown'
                    destination = value[12] if len(value) > 12 else 'Unknown'
                    
                    # Only include flights arriving to ICT or departing from ICT
                    # This captures planes currently in the air heading to Wichita
                    if origin != 'ICT' and destination != 'ICT':
                        continue
                    
                    # Determine flight type and status
                    is_arrival = destination == 'ICT'
                    is_departure = origin == 'ICT'
                    
                    # More descriptive status based on flight direction
                    if is_arrival:
                        status = 'Arriving'
                    elif is_departure:
                        status = 'Departing'
                    else:
                        status = 'En Route'
                    
                    # More descriptive status based on flight direction
                    if is_arrival:
                        status = 'Arriving'
                    elif is_departure:
                        status = 'Departing'
                    else:
                        status = 'En Route'
                    
                    # Flightradar24 array format
                    flight = {
                        'Flight_Number': value[13] if len(value) > 13 else key,  # callsign
                        'hex': key,
                        'latitude': value[1],
                        'longitude': value[2],
                        'heading': value[3],
                        'altitude': value[4],
                        'ground_speed': value[5],
                        'aircraft_type': value[8] if len(value) > 8 else 'Unknown',
                        'registration': value[9] if len(value) > 9 else 'N/A',
                        'origin': origin,
                        'destination': destination,
                        'Origin': origin,
                        'Destination': destination,
                        'Airline': value[18] if len(value) > 18 else 'Unknown',
                        'Type': 'Arrival' if is_arrival else 'Departure',
                        'Status': status,
                        'source': 'Flightradar24'
                    }
                    flights.append(flight)
            
            logger.info(f"Fetched {len(flights)} ICT-bound flights from Flightradar24 (expanded search area)")
            
            # Cache in both memory and Redis
            self.cached_data[cache_key] = flights
            self.last_fetch[cache_key] = datetime.now()
            self.redis_cache.set(cache_key, flights, ttl=15)
            
            # Log operation
            try:
                from operations_logger import log_data_fetch
                log_data_fetch(f"Flightradar24 data fetched: {len(flights)} flights", "success")
            except:
                pass
            
            return flights
            
        except Exception as e:
            logger.warning(f"Failed to fetch Flightradar24 data: {e}")
            return []
    
    def fetch_airportia_data(self, airport_code: str = 'ICT') -> Dict[str, List[Dict]]:
        """
        Scrape live arrivals and departures from Airportia
        
        Args:
            airport_code: IATA airport code (default: ICT)
        
        Returns:
            Dict with 'arrivals' and 'departures' lists
        """
        cache_key = f'airportia_{airport_code}'
        if self._is_cached(cache_key):
            return self.cached_data[cache_key]
        
        try:
            from bs4 import BeautifulSoup
            
            arrivals = []
            departures = []
            
            # Fetch arrivals
            arr_url = f"https://www.airportia.com/united-states/wichita-mid-continent-airport/arrivals/"
            dep_url = f"https://www.airportia.com/united-states/wichita-mid-continent-airport/departures/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Parse arrivals
            try:
                resp = requests.get(arr_url, headers=headers, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find all table rows - Airportia uses plain <table> with <tr> elements
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header row
                    for row in rows[:30]:  # Get up to 30 flights
                        cols = row.find_all('td')
                        if len(cols) >= 7:  # Flight, From, Airline, Date, Scheduled, Arrival, Status
                            flight_num = cols[0].get_text(strip=True)
                            origin = cols[1].get_text(strip=True)
                            airline = cols[2].get_text(strip=True)
                            date_str = cols[3].get_text(strip=True)
                            scheduled = cols[4].get_text(strip=True)
                            actual = cols[5].get_text(strip=True)
                            status = cols[6].get_text(strip=True)
                            
                            # Convert to full ISO 8601 datetime
                            scheduled_dt = self._parse_flight_datetime(date_str, scheduled)
                            actual_dt = self._parse_flight_datetime(date_str, actual) if actual else scheduled_dt
                            
                            if flight_num and origin:  # Only add if we have minimal data
                                arrivals.append({
                                    'Flight_Number': flight_num,
                                    'Airline': airline or 'Unknown',
                                    'Origin': self.normalize_airport_code(origin),
                                    'Scheduled_Time': scheduled_dt,
                                    'Actual_Time': actual_dt,
                                    'Status': status or 'Unknown',
                                    'Type': 'Arrival',
                                    'Destination': airport_code,
                                    'source': 'Airportia'
                                })
            except Exception as e:
                logger.warning(f"Could not parse Airportia arrivals: {e}")
            
            # Parse departures
            try:
                resp = requests.get(dep_url, headers=headers, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find all table rows
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header row
                    for row in rows[:30]:  # Get up to 30 flights
                        cols = row.find_all('td')
                        if len(cols) >= 7:  # Flight, To, Airline, Date, Scheduled, Departure, Status
                            flight_num = cols[0].get_text(strip=True)
                            destination = cols[1].get_text(strip=True)
                            airline = cols[2].get_text(strip=True)
                            date_str = cols[3].get_text(strip=True)
                            scheduled = cols[4].get_text(strip=True)
                            actual = cols[5].get_text(strip=True)
                            status = cols[6].get_text(strip=True)
                            
                            # Convert to full ISO 8601 datetime
                            scheduled_dt = self._parse_flight_datetime(date_str, scheduled)
                            actual_dt = self._parse_flight_datetime(date_str, actual) if actual else scheduled_dt
                            
                            if flight_num and destination:
                                departures.append({
                                    'Flight_Number': flight_num,
                                    'Airline': airline or 'Unknown',
                                    'Destination': self.normalize_airport_code(destination),
                                    'Scheduled_Time': scheduled_dt,
                                    'Actual_Time': actual_dt,
                                    'Status': status or 'Unknown',
                                    'Type': 'Departure',
                                    'Origin': airport_code,
                                    'source': 'Airportia'
                                })
            except Exception as e:
                logger.warning(f"Could not parse Airportia departures: {e}")
            
            result = {'arrivals': arrivals, 'departures': departures}
            logger.info(f"Fetched {len(arrivals)} arrivals, {len(departures)} departures from Airportia")
            
            # Cache in both memory and Redis
            self.cached_data[cache_key] = result
            self.last_fetch[cache_key] = datetime.now()
            self.redis_cache.set(cache_key, result, ttl=15)
            return result
            
        except Exception as e:
            logger.warning(f"Failed to fetch Airportia data: {e}")
            return {'arrivals': [], 'departures': []}
    
    def fetch_bts_statistics(self, airport_code: str = 'ICT') -> Dict[str, Any]:
        """
        Fetch Bureau of Transportation Statistics data
        
        Note: BTS provides downloadable datasets, not real-time API.
        This method provides structure for future integration.
        
        Args:
            airport_code: Airport code
        
        Returns:
            Dict with statistical data
        """
        cache_key = f'bts_{airport_code}'
        if self._is_cached(cache_key):
            return self.cached_data[cache_key]
        
        # BTS data would typically be pre-downloaded CSV files
        # or scraped from their Transtats interface
        # For now, return placeholder structure
        
        stats = {
            'airport': airport_code,
            'passenger_stats': {
                'monthly_enplanements': None,
                'yearly_total': None,
                'year_over_year_change': None
            },
            'airline_performance': {
                'on_time_percentage': None,
                'cancellation_rate': None,
                'delay_statistics': None
            },
            'financial_data': {
                'baggage_fees': {},
                'change_fees': {},
                'fuel_costs': {}
            },
            'source': 'BTS (placeholder)',
            'note': 'BTS data requires CSV import or API key'
        }
        
        logger.info(f"BTS statistics structure prepared for {airport_code}")
        return stats
    
    def get_all_flights(self) -> List[Dict]:
        """
        Aggregate flights from all sources
        
        Returns:
            Combined list of all flight data
        """
        all_flights = []
        
        # Try Flightradar24 first (most comprehensive)
        fr24_flights = self.fetch_flightradar24_data()
        all_flights.extend(fr24_flights)
        
        # Add Airportia data
        airportia = self.fetch_airportia_data()
        all_flights.extend(airportia.get('arrivals', []))
        all_flights.extend(airportia.get('departures', []))
        
        # Deduplicate by flight number
        seen = set()
        unique_flights = []
        for flight in all_flights:
            fnum = flight.get('Flight_Number', '')
            if fnum and fnum not in seen:
                seen.add(fnum)
                unique_flights.append(flight)
        
        # Save all flights to both SQLite (legacy) and HDF5 (hierarchical)
        if unique_flights:
            # Attach weather snapshots to each flight
            for flight in unique_flights:
                # Get weather for the relevant airport (origin for departures, destination for arrivals)
                if flight.get('Type') == 'Arrival':
                    airport = 'ICT'  # Weather at destination
                else:
                    airport = flight.get('Origin', 'ICT')  # Weather at origin
                
                weather = self.get_weather_snapshot(airport)
                flight['weather_snapshot'] = weather
            
            self.history_db.save_flights_batch(unique_flights)
            
            # Save to HDF5 with hierarchical structure
            for flight in unique_flights:
                flight_type = 'arrivals' if flight.get('Type') == 'Arrival' else 'departures'
                
                # Prepare HDF5 flight data
                hdf5_flight = {
                    'flight_number': flight.get('Flight_Number', ''),
                    'airline': flight.get('Airline', ''),
                    'origin': flight.get('Origin', ''),
                    'destination': flight.get('Destination', ''),
                    'scheduled_time': flight.get('Scheduled_Time', ''),
                    'actual_time': flight.get('Actual_Time'),
                    'estimated_time': flight.get('Estimated'),
                    'status': flight.get('Status', ''),
                    'gate': flight.get('Gate'),
                    'terminal': flight.get('Terminal'),
                    'aircraft': flight.get('Aircraft_Type'),
                    'registration': flight.get('registration', ''),
                    'weather_snapshot': flight.get('weather_snapshot', {})
                }
                
                self.hdf5_storage.add_flight(hdf5_flight, flight_type)
        
        logger.info(f"Aggregated {len(unique_flights)} unique flights from all sources")
        
        # Log operation
        try:
            from operations_logger import log_data_fetch
            arrivals = sum(1 for f in unique_flights if f.get('Type') == 'Arrival')
            departures = sum(1 for f in unique_flights if f.get('Type') == 'Departure')
            log_data_fetch(f"Flight data aggregated: {arrivals} arrivals, {departures} departures", "success")
        except:
            pass
        
        return unique_flights
    
    def get_todays_history(self) -> Dict[str, List[Dict]]:
        """
        Get all flights detected today from history database
        Uses HDF5 hierarchical storage for better performance
        
        Returns:
            Dict with 'arrivals' and 'departures' lists from today's history
        """
        # Try HDF5 first (faster, hierarchical)
        try:
            arrivals = self.hdf5_storage.get_flights('arrivals', days=1)
            departures = self.hdf5_storage.get_flights('departures', days=1)
            
            if arrivals or departures:
                return {
                    'arrivals': arrivals,
                    'departures': departures
                }
        except Exception as e:
            logger.warning(f"HDF5 retrieval failed, falling back to SQLite: {e}")
        
        # Fallback to SQLite
        return self.history_db.get_todays_flights()
    
    def get_history_stats(self) -> Dict:
        """Get statistics about flight history from HDF5"""
        try:
            hdf5_stats = self.hdf5_storage.get_statistics()
            
            # Merge with SQLite stats for comparison
            sqlite_stats = self.history_db.get_flight_stats()
            
            return {
                'hdf5': hdf5_stats,
                'sqlite': sqlite_stats,
                'primary_storage': 'HDF5'
            }
        except Exception as e:
            logger.error(f"Error getting HDF5 stats: {e}")
            return self.history_db.get_flight_stats()
    
    def _is_cached(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cached_data or key not in self.last_fetch:
            return False
        
        age = (datetime.now() - self.last_fetch[key]).total_seconds()
        return age < self.cache_timeout
    
    def get_weather_snapshot(self, airport_code: str) -> Dict:
        """
        Get current weather for a specific airport for flight record
        
        Args:
            airport_code: 3-letter IATA code (e.g., 'ICT', 'DFW')
        
        Returns:
            Weather data dict with temperature, wind, precipitation, etc.
        """
        # Airport coordinates
        airports = {
            'ICT': {'lat': 37.75, 'lon': -97.37},
            'DFW': {'lat': 32.90, 'lon': -97.04},
            'DEN': {'lat': 39.86, 'lon': -104.67},
            'ATL': {'lat': 33.64, 'lon': -84.43},
            'PHX': {'lat': 33.43, 'lon': -112.01},
            'ORD': {'lat': 41.98, 'lon': -87.90},
            'IAH': {'lat': 29.98, 'lon': -95.34},
            'MSP': {'lat': 44.88, 'lon': -93.22},
        }
        
        if airport_code not in airports:
            return {}
        
        try:
            info = airports[airport_code]
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
                weather_code = current.get('weathercode', 0)
                conditions = {
                    0: 'Clear', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Overcast',
                    45: 'Foggy', 48: 'Foggy', 51: 'Light Drizzle', 53: 'Drizzle', 55: 'Heavy Drizzle',
                    61: 'Light Rain', 63: 'Rain', 65: 'Heavy Rain', 71: 'Light Snow', 73: 'Snow', 75: 'Heavy Snow',
                    80: 'Light Showers', 81: 'Showers', 82: 'Heavy Showers', 95: 'Thunderstorm'
                }
                
                visibility_m = current.get('visibility', 10000)
                visibility_miles = round(visibility_m * 0.000621371, 1)
                
                return {
                    'Temperature_F': int(current.get('temperature_2m', 70)),
                    'Condition': conditions.get(weather_code, 'Unknown'),
                    'Wind_Speed_mph': int(current.get('windspeed_10m', 0)),
                    'Visibility_miles': visibility_miles,
                    'Humidity_percent': int(current.get('relative_humidity_2m', 50)),
                    'Precipitation_inches': round(current.get('precipitation', 0.0), 2),
                    'Precipitation_probability': int(current.get('precipitation_probability', 0))
                }
        except Exception as e:
            logger.warning(f"Could not fetch weather for {airport_code}: {e}")
        
        return {}


class AirportStatistics:
    """Fetch and manage airport statistics from various sources"""
    
    @staticmethod
    def fetch_nas_status() -> Dict[str, Any]:
        """
        Fetch National Airspace System status
        
        Returns:
            NAS status data
        """
        try:
            # FAA NAS Status API
            url = "https://nasstatus.faa.gov/api/airport-status-information"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info("Fetched NAS status data")
            return data
            
        except Exception as e:
            logger.warning(f"Failed to fetch NAS status: {e}")
            return {}
    
    @staticmethod
    def get_airport_info(airport_code: str = 'ICT') -> Dict[str, Any]:
        """
        Get comprehensive airport information
        
        Args:
            airport_code: IATA code
        
        Returns:
            Airport metadata and statistics
        """
        info = {
            'code': airport_code,
            'name': 'Wichita Dwight D. Eisenhower National Airport',
            'city': 'Wichita',
            'state': 'Kansas',
            'country': 'USA',
            'latitude': 37.6499,
            'longitude': -97.4331,
            'elevation_ft': 1333,
            'timezone': 'America/Chicago',
            'runways': [
                {'id': '01L/19R', 'length_ft': 10301, 'width_ft': 150},
                {'id': '01R/19L', 'length_ft': 7302, 'width_ft': 150},
                {'id': '14/32', 'length_ft': 6301, 'width_ft': 100}
            ],
            'terminals': 1,
            'gates': 16,
            'airlines_count': 7,
            'passenger_capacity_annual': 3000000,
            'cargo_capacity_annual': 50000,
            'links': {
                'official': 'https://www.flywichita.com/',
                'wikipedia': 'https://en.wikipedia.org/wiki/Wichita_Dwight_D._Eisenhower_National_Airport',
                'flightradar24': 'https://www.flightradar24.com/airport/ict',
                'airportia': 'https://www.airportia.com/united-states/wichita-mid-continent-airport/'
            }
        }
        
        return info


# Singleton instance
_aggregator = None

def get_aggregator() -> FlightDataAggregator:
    """Get singleton FlightDataAggregator instance"""
    global _aggregator
    if _aggregator is None:
        _aggregator = FlightDataAggregator()
    return _aggregator
