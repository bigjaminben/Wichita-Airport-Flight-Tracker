"""
Migration script to convert SQLite flight data to HDF5 hierarchical format
"""

import sqlite3
from datetime import datetime
import logging
from hdf5_storage import FlightHDF5Storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_sqlite_to_hdf5():
    """Migrate all data from SQLite to HDF5"""
    
    logger.info("Starting migration from SQLite to HDF5...")
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('flight_history.db')
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()
    
    # Initialize HDF5 storage
    hdf5_storage = FlightHDF5Storage()
    
    try:
        # Get all flights from SQLite
        cursor.execute("""
            SELECT 
                flight_number,
                airline,
                origin,
                destination,
                scheduled_time,
                actual_time,
                status,
                aircraft_type,
                flight_type,
                first_seen,
                altitude,
                ground_speed,
                source
            FROM flights
            ORDER BY scheduled_time
        """)
        
        flights = cursor.fetchall()
        total = len(flights)
        
        logger.info(f"Found {total} flights to migrate")
        
        migrated = 0
        errors = 0
        
        for idx, flight in enumerate(flights, 1):
            try:
                # Convert to dict
                flight_data = {
                    'flight_number': flight['flight_number'],
                    'airline': flight['airline'],
                    'origin': flight['origin'],
                    'destination': flight['destination'],
                    'scheduled_time': flight['scheduled_time'],
                    'actual_time': flight['actual_time'],
                    'status': flight['status'],
                    'aircraft': flight['aircraft_type'],
                    'altitude': flight['altitude'],
                    'ground_speed': flight['ground_speed'],
                    'source': flight['source'],
                    'first_seen': flight['first_seen']
                }
                
                # Determine flight type for hierarchical storage
                flight_type = 'arrivals' if flight['flight_type'] == 'arrival' else 'departures'
                
                # Add to HDF5
                success = hdf5_storage.add_flight(flight_data, flight_type)
                
                if success:
                    migrated += 1
                else:
                    errors += 1
                
                # Progress update every 100 flights
                if idx % 100 == 0:
                    logger.info(f"Progress: {idx}/{total} ({migrated} migrated, {errors} errors)")
                    
            except Exception as e:
                logger.error(f"Error migrating flight {flight['flight_number']}: {e}")
                errors += 1
        
        # Get final statistics
        stats = hdf5_storage.get_statistics()
        
        logger.info("=" * 60)
        logger.info("Migration Complete!")
        logger.info(f"Total flights processed: {total}")
        logger.info(f"Successfully migrated: {migrated}")
        logger.info(f"Errors: {errors}")
        logger.info(f"\nHDF5 Statistics:")
        logger.info(f"  Total arrivals: {stats['total_arrivals']}")
        logger.info(f"  Total departures: {stats['total_departures']}")
        logger.info(f"  Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
        logger.info(f"  File size: {stats['file_size_mb']} MB")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()

if __name__ == "__main__":
    migrate_sqlite_to_hdf5()
