"""
Health Monitor and Logging System
Monitors service health, logs activity, and provides status dashboard
"""
import logging
import logging.handlers
import json
import psutil
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import requests
import time

# Setup directories
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)


class HealthMonitor:
    """Monitor service health and performance"""
    
    def __init__(self):
        self.status_file = LOG_DIR / 'health_status.json'
        self.api_url = 'http://127.0.0.1:5001'
        
        # Setup rotating file handler for monitoring log
        self.logger = logging.getLogger('HealthMonitor')
        self.logger.setLevel(logging.INFO)
        
        # Rotating log (10MB max, keep 5 files)
        handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / 'health.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        
        self.logger.info('Health monitor initialized')
    
    def check_api_health(self) -> Dict:
        """Check if the API is responding"""
        try:
            response = requests.get(f'{self.api_url}/api/flights', timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'healthy',
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'arrivals_count': len(data.get('arrivals', [])),
                    'departures_count': len(data.get('departures', []))
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': f'HTTP {response.status_code}'
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'status': 'down',
                'error': 'Connection refused - service may be down'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_database_health(self) -> Dict:
        """Check database connectivity and size"""
        try:
            db_path = Path(__file__).parent / 'flight_history.db'
            
            if not db_path.exists():
                return {
                    'status': 'missing',
                    'error': 'Database file not found'
                }
            
            # Check database size
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            
            # Check connectivity
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get record count
            cursor.execute('SELECT COUNT(*) FROM flights')
            total_records = cursor.fetchone()[0]
            
            # Get today's count
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute('SELECT COUNT(*) FROM flights WHERE first_seen >= ?', (today,))
            today_records = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'status': 'healthy',
                'size_mb': round(db_size_mb, 2),
                'total_records': total_records,
                'today_records': today_records
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_system_resources(self) -> Dict:
        """Check system resource usage"""
        try:
            return {
                'status': 'healthy',
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage(Path.cwd()).percent
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_backup_status(self) -> Dict:
        """Check backup system status"""
        try:
            backup_dir = Path(__file__).parent / 'backups'
            
            if not backup_dir.exists():
                return {
                    'status': 'warning',
                    'message': 'Backup directory not found'
                }
            
            # Get backup files
            backup_files = list(backup_dir.glob('flight_history_*.db*'))
            
            if not backup_files:
                return {
                    'status': 'warning',
                    'message': 'No backups found'
                }
            
            # Get latest backup
            latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
            backup_age_hours = (time.time() - latest_backup.stat().st_mtime) / 3600
            
            # Total backup size
            total_size_mb = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)
            
            status = 'healthy' if backup_age_hours < 2 else 'warning'
            
            return {
                'status': status,
                'total_backups': len(backup_files),
                'total_size_mb': round(total_size_mb, 2),
                'latest_backup_age_hours': round(backup_age_hours, 1),
                'latest_backup': latest_backup.name
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def run_health_check(self) -> Dict:
        """Run complete health check"""
        self.logger.info('Running health check')
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'api': self.check_api_health(),
            'database': self.check_database_health(),
            'system': self.check_system_resources(),
            'backups': self.check_backup_status()
        }
        
        # Determine overall status
        statuses = [
            health_status['api']['status'],
            health_status['database']['status'],
            health_status['system']['status'],
            health_status['backups']['status']
        ]
        
        if 'down' in statuses or 'error' in statuses:
            health_status['overall'] = 'critical'
        elif 'unhealthy' in statuses:
            health_status['overall'] = 'degraded'
        elif 'warning' in statuses:
            health_status['overall'] = 'warning'
        else:
            health_status['overall'] = 'healthy'
        
        # Save status to file
        with open(self.status_file, 'w') as f:
            json.dump(health_status, f, indent=2)
        
        # Log any issues
        if health_status['overall'] != 'healthy':
            self.logger.warning(f"Health check status: {health_status['overall']}")
            for component, status in health_status.items():
                if isinstance(status, dict) and status.get('status') in ['error', 'unhealthy', 'down']:
                    self.logger.warning(f"{component}: {status.get('error', 'unhealthy')}")
        else:
            self.logger.info('Health check passed - all systems healthy')
        
        return health_status
    
    def get_recent_logs(self, log_file='service.log', lines=100) -> list:
        """Get recent log entries"""
        try:
            log_path = LOG_DIR / log_file
            
            if not log_path.exists():
                return []
            
            with open(log_path, 'r') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
                
        except Exception as e:
            self.logger.error(f'Failed to read logs: {e}')
            return []


def setup_application_logging():
    """Setup centralized logging for the entire application"""
    
    # Create logs directory
    LOG_DIR.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Rotating file handler for main application log (50MB max, keep 10 files)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'application.log',
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Error-only handler (10MB max, keep 5 files)
    error_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'errors.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    logging.info('Centralized logging initialized')
    logging.info(f'Log directory: {LOG_DIR}')


def monitor_loop(interval_seconds=300):
    """Run continuous health monitoring"""
    monitor = HealthMonitor()
    
    logging.info(f'Starting health monitor - checking every {interval_seconds} seconds')
    
    while True:
        try:
            status = monitor.run_health_check()
            
            # Alert on critical status
            if status['overall'] == 'critical':
                logging.error('CRITICAL: Service health check failed!')
                logging.error(f'Status: {json.dumps(status, indent=2)}')
            
            time.sleep(interval_seconds)
            
        except Exception as e:
            logging.error(f'Monitor loop error: {e}', exc_info=True)
            time.sleep(60)  # Wait 1 minute on error


if __name__ == '__main__':
    setup_application_logging()
    monitor_loop()
