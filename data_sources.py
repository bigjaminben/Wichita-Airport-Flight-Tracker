"""
ICT Airport Operations Intelligence Platform - Data Sources Module
Enterprise Data Aggregation & Validation

@fileoverview: Aggregates real-time flight data from Flightradar24 ADS-B radar.
               Implements airline filtering to show ONLY carriers operating at ICT.
               Provides weather data integration and caching.

@version: 2.1.0
@author: Deloitte Consulting LLP
@copyright: 2025 Deloitte Consulting LLP. All rights reserved.

Features:
- Real-time ADS-B radar data from Flightradar24
- Airline whitelist filtering (only ICT operators)
- Redis-powered caching (30s TTL)
- Comprehensive error handling and logging
- Geographic bounds filtering for ICT airport area
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

# Real ICT operators - WHITELIST (only these airlines operate at ICT)
# G4 = Allegiant, AA = American, DL = Delta, WN = Southwest, UA = United, 5A = Alpine
REAL_ICT_AIRLINES = {'G4', 'AA', 'DL', 'WN', 'UA', '5A'}

logger.info(f"ICT Airline Filter: Only accepting {REAL_ICT_AIRLINES}")


class FlightDataAggregator:
    """
    Aggregates flight data from Flightradar24 with airline filtering
    
    Features:
    - Real-time ADS-B radar data
    - Airline whitelist filtering (only ICT operators)
    - Redis caching with 30s TTL
    - HDF5 historical storage integration
    - Geographic bounds filtering
    """
    
    def __init__(self):
        self.cache_timeout = 30  # seconds (optimized for real-time data)
        self.last_fetch = {}
        self.cached_data = {}
        self._history_db = None  # Lazy initialization
        self._hdf5_storage = None  # Lazy initialization
        self._redis_cache = None  # Lazy initialization
    
    @property
    def history_db(self):
        """Lazy initialization of FlightHistoryDB"""
        if self._history_db is None:
            self._history_db = FlightHistoryDB()
        return self._history_db
    
    @property
    def hdf5_storage(self):
        """Lazy initialization of HDF5 storage"""
        if self._hdf5_storage is None:
            self._hdf5_storage = get_storage()
        return self._hdf5_storage
    
    @property
    def redis_cache(self):
        """Lazy initialization of Redis cache"""
        if self._redis_cache is None:
            self._redis_cache = get_cache()
        return self._redis_cache
    
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
            
            response = requests.get(url, params=params, headers=headers, timeout=8)
            response.raise_for_status()
            
            data = response.json()
            flights = []
            
            # ONLY airlines that actually operate at ICT (Wichita, Kansas)
            # No code-share partners - only actual operating carriers
            REAL_ICT_AIRLINES = {
                'G4': 'Allegiant Air',
                'AA': 'American Airlines', 
                'DL': 'Delta Air Lines',
                'WN': 'Southwest Airlines',
                'UA': 'United Airlines',
                '5A': 'Alpine Air Express'  # Small regional cargo/charter
            }
            
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
                    flight_number = value[13] if len(value) > 13 else key  # callsign
                    airline_code = flight_number[:2] if len(flight_number) >= 2 else ''
                    
                    # FILTER: Only include real airlines that operate at ICT
                    # This removes code-share partners (AC, LH, EK, AF, KL, VS, etc.)
                    if airline_code not in REAL_ICT_AIRLINES:
                        continue
                    
                    flight = {
                        'Flight_Number': flight_number,
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
                        'Airline': REAL_ICT_AIRLINES.get(airline_code, 'Unknown'),  # Use real airline name
                        'Type': 'Arrival' if is_arrival else 'Departure',
                        'Status': status,
                        'source': 'Flightradar24'
                    }
                    flights.append(flight)
            
            logger.info(f"Fetched {len(flights)} ICT-bound flights from Flightradar24 (expanded search area)")
            
            # Cache in both memory and Redis
            self.cached_data[cache_key] = flights
            self.last_fetch[cache_key] = datetime.now()
            self.redis_cache.set(cache_key, flights, ttl=30)
            
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
        DISABLED - Airportia was returning unrealistic data (code-share flights from 
        international carriers that don't actually operate at ICT)
        
        Use get_all_flights() instead which uses ONLY Flightradar24 with airline filtering
        """
        logger.warning("fetch_airportia_data() is disabled - use get_all_flights() instead")
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
        
        # Use ONLY Flightradar24 (real ADS-B radar data, most reliable)
        # Airportia scraping has issues with unreliable/demo data
        fr24_flights = self.fetch_flightradar24_data()
        all_flights.extend(fr24_flights)
        
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
