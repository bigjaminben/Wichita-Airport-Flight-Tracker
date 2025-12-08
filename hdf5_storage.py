"""
HDF5 Storage Module for Flight Tracker
Provides hierarchical data storage with superior compression and performance
Uses PyTables for advanced indexing and faster queries
"""

import h5py
import tables
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional
import json
import threading
from queue import Queue

logger = logging.getLogger(__name__)

class FlightHDF5Storage:
    """Manages flight data in HDF5 format with hierarchical structure and async writes"""
    
    def __init__(self, db_path: str = "flight_history.h5"):
        self.db_path = Path(db_path)
        self.ensure_database()
        
        # Async write queue
        self.write_queue = Queue()
        self.writer_thread = None
        self.stop_writer = threading.Event()
        self._start_async_writer()
    
    def _start_async_writer(self):
        """Start background thread for async writes"""
        if self.writer_thread is None or not self.writer_thread.is_alive():
            self.stop_writer.clear()
            self.writer_thread = threading.Thread(target=self._async_writer_loop, daemon=True)
            self.writer_thread.start()
            logger.info("Async HDF5 writer thread started")
    
    def _async_writer_loop(self):
        """Background loop for processing write queue"""
        while not self.stop_writer.is_set():
            try:
                # Get write task with timeout
                task = self.write_queue.get(timeout=1)
                if task is None:  # Poison pill
                    break
                
                flight_data, flight_type = task
                self._write_flight_sync(flight_data, flight_type)
                self.write_queue.task_done()
            except:
                continue  # Timeout or error, keep looping
    
    def ensure_database(self):
        """Create HDF5 file structure with PyTables indexing if it doesn't exist"""
        if not self.db_path.exists():
            # Use PyTables to create indexed file
            with tables.open_file(str(self.db_path), mode='w') as f:
                # Create hierarchical structure
                f.create_group('/', 'arrivals', 'Arrival flights')
                f.create_group('/', 'departures', 'Departure flights')
                f.create_group('/', 'metadata', 'Metadata')
                
                # Store schema version as attributes
                f.root._v_attrs.schema_version = '2.0'
                f.root._v_attrs.created_at = datetime.now().isoformat()
                f.root._v_attrs.indexed = True
                
                logger.info(f"Created new indexed HDF5 database: {self.db_path}")
    
    def add_flight(self, flight_data: Dict, flight_type: str, async_write: bool = True):
        """
        Add flight data to HDF5 storage (async or sync)
        
        Args:
            flight_data: Flight information dictionary
            flight_type: 'arrivals' or 'departures'
            async_write: If True, queue for async write; if False, write immediately
        
        Returns:
            True if queued/written successfully
        """
        if async_write:
            # Queue for async write
            self.write_queue.put((flight_data, flight_type))
            return True
        else:
            # Write immediately
            return self._write_flight_sync(flight_data, flight_type)
    
    def _write_flight_sync(self, flight_data: Dict, flight_type: str):
        """
        Add flight data to HDF5 storage in hierarchical format
        
        Structure:
        /arrivals/YYYY-MM-DD/flight_number/dataset
        /departures/YYYY-MM-DD/flight_number/dataset
        """
        try:
            with h5py.File(self.db_path, 'a') as f:
                # Extract flight info
                flight_number = flight_data.get('flight_number', 'UNKNOWN')
                scheduled_time = flight_data.get('scheduled_time', datetime.now().isoformat())
                
                # Parse date for hierarchical grouping - handle various formats
                if isinstance(scheduled_time, str):
                    if not scheduled_time or scheduled_time in ('N/A', '', 'None'):
                        # No valid time, use today
                        dt = datetime.now()
                    elif 'T' in scheduled_time or '-' in scheduled_time:
                        # ISO format
                        dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                    elif ':' in scheduled_time:
                        # Time-only format like '05:38' - use today's date
                        time_parts = scheduled_time.split(':')
                        dt = datetime.now().replace(hour=int(time_parts[0]), minute=int(time_parts[1]), second=0, microsecond=0)
                    else:
                        dt = datetime.now()
                else:
                    dt = scheduled_time if scheduled_time else datetime.now()
                
                date_key = dt.strftime('%Y-%m-%d')
                
                # Create hierarchical path: /flight_type/date/flight_number
                base_group = f[flight_type]
                
                # Create date group if needed
                if date_key not in base_group:
                    date_group = base_group.create_group(date_key)
                    date_group.attrs['date'] = date_key
                else:
                    date_group = base_group[date_key]
                
                # Create or update flight group
                if flight_number in date_group:
                    flight_group = date_group[flight_number]
                else:
                    flight_group = date_group.create_group(flight_number)
                
                # Store flight attributes
                flight_group.attrs['flight_number'] = flight_number
                flight_group.attrs['scheduled_time'] = scheduled_time
                flight_group.attrs['last_updated'] = datetime.now().isoformat()
                
                # Store all flight data as attributes (compact for metadata)
                # Include weather snapshot and aircraft registration
                for key, value in flight_data.items():
                    if value is not None and key != 'weather_snapshot':  # Skip nested dict
                        if isinstance(value, (str, int, float, bool)):
                            flight_group.attrs[key] = value
                        else:
                            flight_group.attrs[key] = str(value)
                
                # Store weather snapshot separately
                if 'weather_snapshot' in flight_data and flight_data['weather_snapshot']:
                    weather = flight_data['weather_snapshot']
                    flight_group.attrs['temperature'] = weather.get('Temperature_F', 0)
                    flight_group.attrs['wind_speed'] = weather.get('Wind_Speed_mph', 0)
                    flight_group.attrs['visibility'] = weather.get('Visibility_miles', 0)
                    flight_group.attrs['precipitation'] = weather.get('Precipitation_inches', 0)
                    flight_group.attrs['humidity'] = weather.get('Humidity_percent', 0)
                    flight_group.attrs['weather_condition'] = weather.get('Condition', 'Unknown')
                
                # Create dataset for time-series tracking (status changes)
                dataset_name = 'status_history'
                if dataset_name not in flight_group:
                    # Create extensible dataset for tracking status changes
                    dt_type = h5py.string_dtype(encoding='utf-8')
                    flight_group.create_dataset(
                        dataset_name,
                        shape=(1,),
                        maxshape=(None,),
                        dtype=dt_type,
                        compression='gzip',
                        compression_opts=9
                    )
                    flight_group[dataset_name][0] = json.dumps({
                        'timestamp': datetime.now().isoformat(),
                        'status': flight_data.get('status', 'Unknown'),
                        'gate': flight_data.get('gate'),
                        'terminal': flight_data.get('terminal')
                    })
                else:
                    # Append new status
                    dataset = flight_group[dataset_name]
                    dataset.resize((dataset.shape[0] + 1,))
                    dataset[-1] = json.dumps({
                        'timestamp': datetime.now().isoformat(),
                        'status': flight_data.get('status', 'Unknown'),
                        'gate': flight_data.get('gate'),
                        'terminal': flight_data.get('terminal')
                    })
                
                return True
                
        except Exception as e:
            logger.error(f"Error adding flight to HDF5: {e}")
            return False
    
    def flush_queue(self, timeout: int = 10):
        """Wait for all queued writes to complete"""
        self.write_queue.join()
        logger.info("All queued HDF5 writes completed")
    
    def close(self):
        """Close writer thread and flush queue"""
        logger.info("Shutting down HDF5 async writer...")
        self.flush_queue()
        self.stop_writer.set()
        self.write_queue.put(None)  # Poison pill
        if self.writer_thread:
            self.writer_thread.join(timeout=5)
    
    def get_flights(self, flight_type: str, days: int = 7) -> List[Dict]:
        """
        Retrieve flights from HDF5 storage
        
        Args:
            flight_type: 'arrivals' or 'departures'
            days: Number of days to retrieve
        
        Returns:
            List of flight dictionaries
        """
        flights = []
        
        try:
            with h5py.File(self.db_path, 'r') as f:
                if flight_type not in f:
                    return flights
                
                base_group = f[flight_type]
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Iterate through date groups
                for date_key in base_group.keys():
                    try:
                        date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                        if date_obj < cutoff_date:
                            continue
                    except ValueError:
                        continue
                    
                    date_group = base_group[date_key]
                    
                    # Iterate through flights in this date
                    for flight_number in date_group.keys():
                        flight_group = date_group[flight_number]
                        
                        # Extract flight data from attributes
                        flight_data = {
                            'flight_type': flight_type[:-1]  # Remove 's' from arrivals/departures
                        }
                        
                        for attr_name, attr_value in flight_group.attrs.items():
                            flight_data[attr_name] = attr_value
                        
                        # Get latest status from history
                        if 'status_history' in flight_group:
                            history = flight_group['status_history']
                            if len(history) > 0:
                                latest = json.loads(history[-1])
                                flight_data['current_status'] = latest.get('status')
                                flight_data['status_updated_at'] = latest.get('timestamp')
                        
                        flights.append(flight_data)
                
        except Exception as e:
            logger.error(f"Error retrieving flights from HDF5: {e}")
        
        return flights
    
    def get_flight_history(self, flight_number: str, flight_type: str, date: str) -> Optional[Dict]:
        """Get complete history for a specific flight"""
        try:
            with h5py.File(self.db_path, 'r') as f:
                path = f"{flight_type}/{date}/{flight_number}"
                
                if path not in f:
                    return None
                
                flight_group = f[path]
                
                # Get all attributes
                flight_data = dict(flight_group.attrs)
                
                # Get complete status history
                if 'status_history' in flight_group:
                    history = flight_group['status_history']
                    flight_data['status_history'] = [
                        json.loads(entry) for entry in history[:]
                    ]
                
                return flight_data
                
        except Exception as e:
            logger.error(f"Error getting flight history: {e}")
            return None
    
    def cleanup_old_data(self, days: int = 30):
        """Remove flight data older than specified days"""
        try:
            with h5py.File(self.db_path, 'a') as f:
                cutoff_date = datetime.now() - timedelta(days=days)
                removed_count = 0
                
                for flight_type in ['arrivals', 'departures']:
                    if flight_type not in f:
                        continue
                    
                    base_group = f[flight_type]
                    dates_to_remove = []
                    
                    for date_key in base_group.keys():
                        try:
                            date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                            if date_obj < cutoff_date:
                                dates_to_remove.append(date_key)
                        except ValueError:
                            continue
                    
                    # Remove old date groups
                    for date_key in dates_to_remove:
                        del base_group[date_key]
                        removed_count += 1
                
                logger.info(f"Cleaned up {removed_count} date groups older than {days} days")
                return removed_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        stats = {
            'total_arrivals': 0,
            'total_departures': 0,
            'date_range': {'start': None, 'end': None},
            'file_size_mb': 0
        }
        
        try:
            if self.db_path.exists():
                stats['file_size_mb'] = round(self.db_path.stat().st_size / (1024 * 1024), 2)
            
            with h5py.File(self.db_path, 'r') as f:
                dates = []
                
                for flight_type in ['arrivals', 'departures']:
                    if flight_type not in f:
                        continue
                    
                    base_group = f[flight_type]
                    
                    for date_key in base_group.keys():
                        dates.append(date_key)
                        date_group = base_group[date_key]
                        flight_count = len(date_group.keys())
                        
                        if flight_type == 'arrivals':
                            stats['total_arrivals'] += flight_count
                        else:
                            stats['total_departures'] += flight_count
                
                if dates:
                    stats['date_range']['start'] = min(dates)
                    stats['date_range']['end'] = max(dates)
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
        
        return stats
    
    def export_to_pandas(self, flight_type: str, days: int = 7) -> pd.DataFrame:
        """Export flight data to pandas DataFrame for analysis"""
        flights = self.get_flights(flight_type, days)
        
        if not flights:
            return pd.DataFrame()
        
        df = pd.DataFrame(flights)
        
        # Convert time columns to datetime
        time_columns = ['scheduled_time', 'actual_time', 'estimated_time']
        for col in time_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def close(self):
        """Close any open connections (HDF5 handles auto-close in context managers)"""
        pass


# Singleton instance
_storage_instance = None

def get_storage() -> FlightHDF5Storage:
    """Get singleton HDF5 storage instance"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = FlightHDF5Storage()
    return _storage_instance
