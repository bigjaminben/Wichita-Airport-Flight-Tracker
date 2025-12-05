"""
Automated Database Backup System
Handles scheduled backups, retention policies, and archival for flight_history.db
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
    def __init__(self, db_path='flight_history.db'):
        self.db_path = Path(db_path)
        self.backup_dir = Path(__file__).parent / 'backups'
        self.archive_dir = self.backup_dir / 'archive'
        
        # Create directories
        self.backup_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
        
        # Backup configuration
        self.config = {
            'hourly_retention': 24,      # Keep last 24 hourly backups
            'daily_retention': 30,       # Keep last 30 daily backups
            'weekly_retention': 12,      # Keep last 12 weekly backups
            'monthly_retention': 12,     # Keep last 12 monthly backups
            'compress_after_days': 7     # Compress backups older than 7 days
        }
        
        logger.info(f'BackupManager initialized - Database: {self.db_path}')
        logger.info(f'Backup directory: {self.backup_dir}')
    
    def create_backup(self, backup_type='manual'):
        """Create a backup of the database"""
        try:
            if not self.db_path.exists():
                logger.warning(f'Database not found: {self.db_path}')
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'flight_history_{backup_type}_{timestamp}.db'
            backup_path = self.backup_dir / backup_filename
            
            # Create backup using SQLite's backup API
            logger.info(f'Creating {backup_type} backup: {backup_filename}')
            
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # Get backup size
            backup_size = backup_path.stat().st_size / 1024  # KB
            logger.info(f'Backup created successfully - Size: {backup_size:.2f} KB')
            
            # Log operation
            try:
                from operations_logger import log_backup
                log_backup(f"{backup_type.capitalize()} backup created ({backup_size:.1f} KB)", "success", str(backup_filename))
            except:
                pass
            
            # Create metadata file
            metadata = {
                'timestamp': timestamp,
                'type': backup_type,
                'size_kb': backup_size,
                'database': str(self.db_path),
                'created': datetime.now().isoformat()
            }
            
            metadata_path = backup_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return backup_path
            
        except Exception as e:
            logger.error(f'Backup failed: {e}', exc_info=True)
            return None
    
    def compress_old_backups(self):
        """Compress backups older than configured threshold"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config['compress_after_days'])
            compressed_count = 0
            
            for backup_file in self.backup_dir.glob('*.db'):
                # Skip if already compressed
                if backup_file.with_suffix('.db.gz').exists():
                    continue
                
                # Check file age
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    logger.info(f'Compressing old backup: {backup_file.name}')
                    
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
