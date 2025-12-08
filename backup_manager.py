"""
Automated Database Backup System
Handles scheduled backups, retention policies, and archival for flight databases
Supports both SQLite and HDF5 hierarchical data formats
"""
import sqlite3
import shutil
import gzip
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging
import schedule
import time

# Setup logging
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BackupManager')


class BackupManager:
    def __init__(self, db_path='flight_history.db', hdf5_path='flight_history.h5'):
        self.db_path = Path(db_path)
        self.hdf5_path = Path(hdf5_path)
        self.backup_dir = Path(__file__).parent / 'backups'
        self.archive_dir = self.backup_dir / 'archive'
        
        # Create directories
        self.backup_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
        
        # Backup configuration - optimized retention
        self.config = {
            'hourly_retention': 12,      # Keep last 12 hourly backups (reduced from 24)
            'daily_retention': 14,       # Keep last 14 daily backups (reduced from 30)
            'weekly_retention': 8,       # Keep last 8 weekly backups (reduced from 12)
            'monthly_retention': 6,      # Keep last 6 monthly backups (reduced from 12)
            'compress_after_days': 3     # Compress backups older than 3 days (reduced from 7)
        }
        
        logger.info(f'BackupManager initialized')
        logger.info(f'  SQLite: {self.db_path}')
        logger.info(f'  HDF5: {self.hdf5_path}')
        logger.info(f'  Backup directory: {self.backup_dir}')
    
    def create_backup(self, backup_type='manual'):
        """Create backups of both SQLite and HDF5 databases"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backups_created = []
            total_size = 0
            
            # Backup SQLite if exists
            if self.db_path.exists():
                sqlite_backup = self._backup_sqlite(backup_type, timestamp)
                if sqlite_backup:
                    backups_created.append(('SQLite', sqlite_backup))
                    total_size += sqlite_backup.stat().st_size / 1024
            
            # Backup HDF5 if exists
            if self.hdf5_path.exists():
                hdf5_backup = self._backup_hdf5(backup_type, timestamp)
                if hdf5_backup:
                    backups_created.append(('HDF5', hdf5_backup))
                    total_size += hdf5_backup.stat().st_size / 1024
            
            if backups_created:
                logger.info(f'Backups created: {len(backups_created)} files, {total_size:.2f} KB total')
                
                # Log operation
                try:
                    from operations_logger import log_backup
                    log_backup(f"{backup_type.capitalize()} backup: {len(backups_created)} files ({total_size:.1f} KB)", "success", timestamp)
                except:
                    pass
                
                return backups_created
            else:
                logger.warning('No databases found to backup')
                return None
                
        except Exception as e:
            logger.error(f'Backup failed: {e}', exc_info=True)
            return None
    
    def _backup_sqlite(self, backup_type, timestamp):
        """Backup SQLite database"""
        try:
            backup_filename = f'flight_history_{backup_type}_{timestamp}.db'
            backup_path = self.backup_dir / backup_filename
            
            logger.info(f'Creating SQLite {backup_type} backup: {backup_filename}')
            
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            return backup_path
        except Exception as e:
            logger.error(f'SQLite backup failed: {e}')
            return None
    
    def _backup_hdf5(self, backup_type, timestamp):
        """Backup HDF5 database"""
        try:
            backup_filename = f'flight_history_{backup_type}_{timestamp}.h5'
            backup_path = self.backup_dir / backup_filename
            
            logger.info(f'Creating HDF5 {backup_type} backup: {backup_filename}')
            
            # Simple copy for HDF5 (it's already optimized)
            shutil.copy2(self.hdf5_path, backup_path)
            
            return backup_path
        except Exception as e:
            logger.error(f'HDF5 backup failed: {e}')
            return None
    
    def compress_old_backups(self):
        """Compress backups older than configured threshold (both SQLite and HDF5)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config['compress_after_days'])
            compressed_count = 0
            
            # Compress SQLite backups
            for backup_file in self.backup_dir.glob('*.db'):
                # Skip if already compressed
                if backup_file.with_suffix('.db.gz').exists():
                    continue
                
                # Check file age
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    logger.info(f'Compressing old SQLite backup: {backup_file.name}')
                    
                    # Compress the file
                    with open(backup_file, 'rb') as f_in:
                        with gzip.open(f'{backup_file}.gz', 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove original
                    backup_file.unlink()
                    compressed_count += 1
            
            # Compress HDF5 backups
            for backup_file in self.backup_dir.glob('*.h5'):
                # Skip if already compressed
                if backup_file.with_suffix('.h5.gz').exists():
                    continue
                
                # Check file age
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    logger.info(f'Compressing old HDF5 backup: {backup_file.name}')
                    
                    # Compress the file
                    with open(backup_file, 'rb') as f_in:
                        with gzip.open(f'{backup_file}.gz', 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove original
                    backup_file.unlink()
                    
                    # Also compress metadata if exists
                    metadata_file = backup_file.with_suffix('.json')
                    if metadata_file.exists():
                        with open(metadata_file, 'rb') as f_in:
                            with gzip.open(f'{metadata_file}.gz', 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        metadata_file.unlink()
                    
                    compressed_count += 1
            
            if compressed_count > 0:
                logger.info(f'Compressed {compressed_count} old backups')
                
                # Log operation
                try:
                    from operations_logger import log_backup
                    log_backup(f"Compressed {compressed_count} old backups", "success")
                except:
                    pass
                
        except Exception as e:
            logger.error(f'Compression failed: {e}', exc_info=True)
    
    def cleanup_old_backups(self):
        """Remove backups older than retention policies"""
        try:
            now = datetime.now()
            removed_count = 0
            
            # Get all backup files (including compressed)
            backup_files = list(self.backup_dir.glob('flight_history_*.db*'))
            
            for backup_type, retention_days in [
                ('hourly', self.config['hourly_retention'] / 24),
                ('daily', self.config['daily_retention']),
                ('weekly', self.config['weekly_retention'] * 7),
                ('monthly', self.config['monthly_retention'] * 30)
            ]:
                cutoff_date = now - timedelta(days=retention_days)
                
                # Filter files of this type
                type_files = [f for f in backup_files if f'_{backup_type}_' in f.name]
                
                for backup_file in type_files:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        logger.info(f'Removing old {backup_type} backup: {backup_file.name}')
                        backup_file.unlink()
                        
                        # Remove metadata if exists
                        metadata_file = Path(str(backup_file).replace('.db.gz', '.json.gz').replace('.db', '.json'))
                        if metadata_file.exists():
                            metadata_file.unlink()
                        
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f'Removed {removed_count} old backups per retention policy')
                
        except Exception as e:
            logger.error(f'Cleanup failed: {e}', exc_info=True)
    
    def export_old_data(self, days_old=90):
        """Export data older than threshold to archive"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d')
            archive_file = self.archive_dir / f'archive_{cutoff_date}.json.gz'
            
            logger.info(f'Archiving data older than {cutoff_date}')
            
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Export old flights
            cursor.execute("""
                SELECT * FROM flights 
                WHERE date(timestamp) < date(?)
            """, (cutoff_date,))
            
            old_flights = [dict(row) for row in cursor.fetchall()]
            
            if old_flights:
                logger.info(f'Found {len(old_flights)} old flights to archive')
                
                # Save to compressed JSON
                archive_data = {
                    'cutoff_date': cutoff_date,
                    'archived_at': datetime.now().isoformat(),
                    'flight_count': len(old_flights),
                    'flights': old_flights
                }
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump(archive_data, f, indent=2)
                
                # Delete archived data from main database
                cursor.execute("""
                    DELETE FROM flights 
                    WHERE date(timestamp) < date(?)
                """, (cutoff_date,))
                
                conn.commit()
                logger.info(f'Archived {len(old_flights)} flights to {archive_file.name}')
                logger.info(f'Removed old data from main database')
            else:
                logger.info('No old data to archive')
            
            conn.close()
            
        except Exception as e:
            logger.error(f'Archive export failed: {e}', exc_info=True)
    
    def get_backup_stats(self):
        """Get statistics about current backups"""
        try:
            stats = {
                'total_backups': 0,
                'total_size_mb': 0,
                'by_type': {},
                'oldest_backup': None,
                'newest_backup': None
            }
            
            backup_files = list(self.backup_dir.glob('flight_history_*.db*'))
            
            if not backup_files:
                return stats
            
            stats['total_backups'] = len(backup_files)
            
            for backup_file in backup_files:
                # Get type from filename
                parts = backup_file.stem.split('_')
                if len(parts) >= 3:
                    backup_type = parts[2]
                    
                    if backup_type not in stats['by_type']:
                        stats['by_type'][backup_type] = {'count': 0, 'size_mb': 0}
                    
                    stats['by_type'][backup_type]['count'] += 1
                    
                    size_mb = backup_file.stat().st_size / (1024 * 1024)
                    stats['by_type'][backup_type]['size_mb'] += size_mb
                    stats['total_size_mb'] += size_mb
            
            # Get oldest and newest
            sorted_files = sorted(backup_files, key=lambda f: f.stat().st_mtime)
            stats['oldest_backup'] = datetime.fromtimestamp(sorted_files[0].stat().st_mtime).isoformat()
            stats['newest_backup'] = datetime.fromtimestamp(sorted_files[-1].stat().st_mtime).isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f'Failed to get backup stats: {e}')
            return {'error': str(e)}


def run_backup_scheduler():
    """Run the scheduled backup tasks"""
    logger.info('Starting backup scheduler')
    
    manager = BackupManager()
    
    # Schedule different backup types
    schedule.every().hour.do(lambda: manager.create_backup('hourly'))
    schedule.every().day.at("02:00").do(lambda: manager.create_backup('daily'))
    schedule.every().sunday.at("03:00").do(lambda: manager.create_backup('weekly'))
    schedule.every().day.at("04:00").do(manager.compress_old_backups)
    schedule.every().day.at("05:00").do(manager.cleanup_old_backups)
    schedule.every().sunday.at("06:00").do(lambda: manager.export_old_data(90))
    
    # Create initial backup
    manager.create_backup('startup')
    
    logger.info('Backup scheduler configured:')
    logger.info('  - Hourly backups every hour')
    logger.info('  - Daily backups at 2:00 AM')
    logger.info('  - Weekly backups on Sunday at 3:00 AM')
    logger.info('  - Compression daily at 4:00 AM')
    logger.info('  - Cleanup daily at 5:00 AM')
    logger.info('  - Archive export on Sunday at 6:00 AM')
    
    # Run scheduler loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f'Scheduler error: {e}', exc_info=True)
            time.sleep(60)


if __name__ == '__main__':
    run_backup_scheduler()
