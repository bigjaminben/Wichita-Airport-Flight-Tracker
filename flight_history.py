"""
Flight History Database
Stores all detected flights to provide historical tracking
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import os

logger = logging.getLogger(__name__)

class FlightHistoryDB:
    """Manages flight history storage and retrieval"""
    
    def __init__(self, db_path: str = 'flight_history.db'):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    flight_number TEXT NOT NULL,
                    airline TEXT,
                    origin TEXT,
                    destination TEXT,
                    flight_type TEXT,
                    scheduled_time TEXT,
                    actual_time TEXT,
                    status TEXT,
                    aircraft_type TEXT,
                    aircraft_registration TEXT,
                    altitude INTEGER,
                    ground_speed INTEGER,
                    source TEXT,
                    temperature REAL,
                    wind_speed REAL,
                    visibility REAL,
                    precipitation REAL,
                    humidity INTEGER,
                    weather_condition TEXT,
                    inbound_flight_number TEXT,
                    inbound_delay_minutes INTEGER,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(flight_number, scheduled_time, flight_type)
                )
            ''')
            
            # Create indices for faster queries - optimized
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_flight_lookup 
                ON flights(flight_number, scheduled_time, flight_type)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_first_seen 
                ON flights(first_seen DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_status
                ON flights(status)
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Flight history database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def save_flight(self, flight: Dict):
        """Save or update a flight record"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract flight data
            flight_number = flight.get('Flight_Number', 'UNKNOWN')
            airline = flight.get('Airline', 'Unknown')
            origin = flight.get('Origin', flight.get('origin', 'Unknown'))
            destination = flight.get('Destination', flight.get('destination', 'Unknown'))
            flight_type = flight.get('Type', 'Unknown')
            scheduled_time = flight.get('Scheduled_Time', '')
            actual_time = flight.get('Actual_Time', flight.get('actual_time', ''))
            status = flight.get('Status', 'Unknown')
            aircraft_type = flight.get('aircraft_type', '')
            aircraft_registration = flight.get('registration', flight.get('aircraft_registration', ''))
            altitude = flight.get('altitude', 0)
            ground_speed = flight.get('ground_speed', 0)
            source = flight.get('source', 'Unknown')
            
            # Extract weather snapshot (if provided)
            weather = flight.get('weather_snapshot', {})
            temperature = weather.get('Temperature_F', None)
            wind_speed = weather.get('Wind_Speed_mph', None)
            visibility = weather.get('Visibility_miles', None)
            precipitation = weather.get('Precipitation_inches', None)
            humidity = weather.get('Humidity_percent', None)
            weather_condition = weather.get('Condition', None)
            
            # Extract inbound flight info (for cascading delays)
            inbound_flight = flight.get('inbound_flight_number', None)
            inbound_delay = flight.get('inbound_delay_minutes', None)
            
            # Insert or update
            cursor.execute('''
                INSERT INTO flights (
                    flight_number, airline, origin, destination, flight_type,
                    scheduled_time, actual_time, status, aircraft_type, aircraft_registration,
                    altitude, ground_speed, source,
                    temperature, wind_speed, visibility, precipitation, humidity, weather_condition,
                    inbound_flight_number, inbound_delay_minutes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(flight_number, scheduled_time, flight_type) 
                DO UPDATE SET
                    status = excluded.status,
                    actual_time = excluded.actual_time,
                    altitude = excluded.altitude,
                    ground_speed = excluded.ground_speed,
                    last_updated = CURRENT_TIMESTAMP
            ''', (
                flight_number, airline, origin, destination, flight_type,
                scheduled_time, actual_time, status, aircraft_type,
                altitude, ground_speed, source
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to save flight {flight.get('Flight_Number', 'UNKNOWN')}: {e}")
    
    def save_flights_batch(self, flights: List[Dict]):
        """Save multiple flights efficiently"""
        for flight in flights:
            self.save_flight(flight)
        logger.info(f"Saved {len(flights)} flights to history database")
    
    def get_todays_flights(self) -> Dict[str, List[Dict]]:
        """Get all flights detected today"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get flights from today (midnight to now)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            cursor.execute('''
                SELECT * FROM flights 
                WHERE first_seen >= ? 
                ORDER BY first_seen DESC
            ''', (today,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to dict and separate by type
            arrivals = []
            departures = []
            
            for row in rows:
                flight_dict = dict(row)
                if flight_dict['flight_type'] == 'Arrival':
                    arrivals.append(flight_dict)
                else:
                    departures.append(flight_dict)
            
            return {
                'arrivals': arrivals,
                'departures': departures
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve today's flights: {e}")
            return {'arrivals': [], 'departures': []}
    
    def get_flight_stats(self) -> Dict:
        """Get statistics about today's flights"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Total flights today
            cursor.execute('SELECT COUNT(*) FROM flights WHERE first_seen >= ?', (today,))
            total_today = cursor.fetchone()[0]
            
            # Arrivals today
            cursor.execute('''
                SELECT COUNT(*) FROM flights 
                WHERE first_seen >= ? AND flight_type = 'Arrival'
            ''', (today,))
            arrivals_today = cursor.fetchone()[0]
            
            # Departures today
            cursor.execute('''
                SELECT COUNT(*) FROM flights 
                WHERE first_seen >= ? AND flight_type = 'Departure'
            ''', (today,))
            departures_today = cursor.fetchone()[0]
            
            # Landed flights
            cursor.execute('''
                SELECT COUNT(*) FROM flights 
                WHERE first_seen >= ? AND status LIKE '%Landed%'
            ''', (today,))
            landed = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_today': total_today,
                'arrivals_today': arrivals_today,
                'departures_today': departures_today,
                'landed': landed
            }
            
        except Exception as e:
            logger.error(f"Failed to get flight stats: {e}")
            return {
                'total_today': 0,
                'arrivals_today': 0,
                'departures_today': 0,
                'landed': 0
            }
    
    def cleanup_old_records(self, days_to_keep: int = 7):
        """Remove records older than specified days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            cursor.execute('DELETE FROM flights WHERE first_seen < ?', (cutoff_date,))
            deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old flight records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
    
    def get_flights_by_date_range(self, start_date: str, end_date: str = None):
        """Get flights within a date range (format: YYYY-MM-DD)"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Parse dates and add time range for full day coverage
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            
            cursor.execute("""
                SELECT * FROM flights 
                WHERE first_seen >= ? AND first_seen < ?
                ORDER BY first_seen DESC
            """, (start_datetime, end_datetime))
            
            flights = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return flights
            
        except Exception as e:
            logger.error(f"Failed to get flights by date range: {e}")
            return []
    
    def get_date_range_stats(self, start_date: str, end_date: str = None) -> Dict:
        """Get statistics for a date range (format: YYYY-MM-DD)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Parse dates and add time range
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_flights,
                    SUM(CASE WHEN flight_type = 'Arrival' THEN 1 ELSE 0 END) as arrivals,
                    SUM(CASE WHEN flight_type = 'Departure' THEN 1 ELSE 0 END) as departures,
                    SUM(CASE WHEN status LIKE '%Landed%' THEN 1 ELSE 0 END) as landed,
                    SUM(CASE WHEN status LIKE '%Delayed%' THEN 1 ELSE 0 END) as delayed
                FROM flights
                WHERE first_seen >= ? AND first_seen < ?
            """, (start_datetime, end_datetime))
            
            stats = cursor.fetchone()
            conn.close()
            
            return {
                'total_flights': stats[0] or 0,
                'arrivals': stats[1] or 0,
                'departures': stats[2] or 0,
                'landed': stats[3] or 0,
                'delayed': stats[4] or 0,
                'start_date': start_date,
                'end_date': end_date
            }
            
        except Exception as e:
            logger.error(f"Failed to get date range stats: {e}")
            return {
                'total_flights': 0,
                'arrivals': 0,
                'departures': 0,
                'landed': 0,
                'delayed': 0,
                'start_date': start_date,
                'end_date': end_date or datetime.now().strftime('%Y-%m-%d')
            }

