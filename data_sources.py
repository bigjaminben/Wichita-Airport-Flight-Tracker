"""
Enhanced data sources for Airport Tracker
Integrates multiple real-time and statistical data sources
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from flight_history import FlightHistoryDB

logger = logging.getLogger(__name__)

class FlightDataAggregator:
    """Aggregates flight data from multiple sources"""
    
    def __init__(self):
        self.cache_timeout = 15  # seconds
        self.last_fetch = {}
        self.cached_data = {}
        self.history_db = FlightHistoryDB()  # Initialize history database
        
    def fetch_flightradar24_data(self, bounds: tuple = (34.0, 41.0, -102.0, -92.0)) -> List[Dict]:
        """
        Fetch live flight data from Flightradar24
        
        Args:
            bounds: (lat_min, lat_max, lon_min, lon_max) - Expanded to ~400 mile radius 
                    to capture all flights arriving to ICT (not just overhead)
        
        Returns:
            List of flight dictionaries filtered to ICT arrivals/departures
        """
        cache_key = 'flightradar24'
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
            self.cached_data[cache_key] = flights
            self.last_fetch[cache_key] = datetime.now()
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
                            scheduled = cols[4].get_text(strip=True)
                            actual = cols[5].get_text(strip=True)
                            status = cols[6].get_text(strip=True)
                            
                            if flight_num and origin:  # Only add if we have minimal data
                                arrivals.append({
                                    'Flight_Number': flight_num,
                                    'Airline': airline or 'Unknown',
                                    'Origin': origin,
                                    'Scheduled_Time': scheduled or 'N/A',
                                    'Actual_Time': actual or scheduled,
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
                            scheduled = cols[4].get_text(strip=True)
                            actual = cols[5].get_text(strip=True)
                            status = cols[6].get_text(strip=True)
                            
                            if flight_num and destination:
                                departures.append({
                                    'Flight_Number': flight_num,
                                    'Airline': airline or 'Unknown',
                                    'Destination': destination,
                                    'Scheduled_Time': scheduled or 'N/A',
                                    'Actual_Time': actual or scheduled,
                                    'Status': status or 'Unknown',
                                    'Type': 'Departure',
                                    'Origin': airport_code,
                                    'source': 'Airportia'
                                })
            except Exception as e:
                logger.warning(f"Could not parse Airportia departures: {e}")
            
            result = {'arrivals': arrivals, 'departures': departures}
            logger.info(f"Fetched {len(arrivals)} arrivals, {len(departures)} departures from Airportia")
            
            self.cached_data[cache_key] = result
            self.last_fetch[cache_key] = datetime.now()
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
        
        # Save all flights to history database
        if unique_flights:
            self.history_db.save_flights_batch(unique_flights)
        
        logger.info(f"Aggregated {len(unique_flights)} unique flights from all sources")
        return unique_flights
    
    def get_todays_history(self) -> Dict[str, List[Dict]]:
        """
        Get all flights detected today from history database
        
        Returns:
            Dict with 'arrivals' and 'departures' lists from today's history
        """
        return self.history_db.get_todays_flights()
    
    def get_history_stats(self) -> Dict:
        """Get statistics about today's flight history"""
        return self.history_db.get_flight_stats()
    
    def _is_cached(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cached_data or key not in self.last_fetch:
            return False
        
        age = (datetime.now() - self.last_fetch[key]).total_seconds()
        return age < self.cache_timeout


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
