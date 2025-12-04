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
                    altitude INTEGER,
                    ground_speed INTEGER,
                    source TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(flight_number, scheduled_time, flight_type)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_flight_date 
                ON flights(flight_number, scheduled_time)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_first_seen 
                ON flights(first_seen)
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
            altitude = flight.get('altitude', 0)
            ground_speed = flight.get('ground_speed', 0)
            source = flight.get('source', 'Unknown')
            
            # Insert or update
            cursor.execute('''
                INSERT INTO flights (
                    flight_number, airline, origin, destination, flight_type,
                    scheduled_time, actual_time, status, aircraft_type,
                    altitude, ground_speed, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
