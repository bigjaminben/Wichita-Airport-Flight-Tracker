"""
Daily Operations Logger
Tracks and records all daily operational activities for easy dashboard viewing
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import threading

# Setup logging
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger('OperationsLogger')


class DailyOperationsLog:
    """Manages daily operations tracking and logging"""
    
    def __init__(self, log_file='logs/daily_operations.json'):
        self.log_file = Path(log_file)
        self.lock = threading.Lock()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Create log file if it doesn't exist"""
        if not self.log_file.exists():
            self._save_logs([])
    
    def _load_logs(self) -> List[Dict]:
        """Load existing logs"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to load operations log: {e}")
            return []
    
    def _save_logs(self, logs: List[Dict]):
        """Save logs to file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save operations log: {e}")
    
    def log_operation(self, category: str, operation: str, status: str = 'success', details: str = None):
        """
        Log a daily operation
        
        Args:
            category: Type of operation (e.g., 'backup', 'data_fetch', 'system', 'monitoring')
            operation: Description of the operation
            status: 'success', 'warning', 'error', 'info'
            details: Optional additional details
        """
        with self.lock:
            logs = self._load_logs()
            
            entry = {
                'timestamp': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%I:%M:%S %p'),
                'category': category,
                'operation': operation,
                'status': status,
                'details': details
            }
            
            logs.append(entry)
            
            # Keep only last 500 entries to prevent file from growing too large
            if len(logs) > 500:
                logs = logs[-500:]
            
            self._save_logs(logs)
            logger.info(f"Logged operation: {category} - {operation} [{status}]")
    
    def get_today_operations(self) -> List[Dict]:
        """Get all operations from today"""
        today = datetime.now().strftime('%Y-%m-%d')
        logs = self._load_logs()
        return [log for log in logs if log.get('date') == today]
    
    def get_operations_by_date(self, date_str: str) -> List[Dict]:
        """Get operations for a specific date (YYYY-MM-DD)"""
        logs = self._load_logs()
        return [log for log in logs if log.get('date') == date_str]
    
    def get_recent_operations(self, hours: int = 24) -> List[Dict]:
        """Get operations from the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        logs = self._load_logs()
        
        recent = []
        for log in logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if log_time >= cutoff:
                    recent.append(log)
            except:
                continue
        
        return recent
    
    def get_daily_summary(self, date_str: str = None) -> Dict:
        """Get summary statistics for a specific date"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        logs = self.get_operations_by_date(date_str)
        
        summary = {
            'date': date_str,
            'total_operations': len(logs),
            'by_category': {},
            'by_status': {
                'success': 0,
                'warning': 0,
                'error': 0,
                'info': 0
            },
            'timeline': []
        }
        
        for log in logs:
            # Count by category
            category = log.get('category', 'unknown')
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count by status
            status = log.get('status', 'info')
            if status in summary['by_status']:
                summary['by_status'][status] += 1
            
            # Add to timeline
            summary['timeline'].append({
                'time': log.get('time'),
                'category': category,
                'operation': log.get('operation'),
                'status': status
            })
        
        return summary
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove logs older than specified days"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
        
        with self.lock:
            logs = self._load_logs()
            filtered_logs = [log for log in logs if log.get('date', '9999-99-99') >= cutoff_date]
            
            removed_count = len(logs) - len(filtered_logs)
            if removed_count > 0:
                self._save_logs(filtered_logs)
                logger.info(f"Cleaned up {removed_count} old operation logs")


# Global instance
operations_log = DailyOperationsLog()


# Convenience functions
def log_backup(operation: str, status: str = 'success', details: str = None):
    """Log a backup operation"""
    operations_log.log_operation('Backup', operation, status, details)


def log_data_fetch(operation: str, status: str = 'success', details: str = None):
    """Log a data fetch operation"""
    operations_log.log_operation('Data Fetch', operation, status, details)


def log_system(operation: str, status: str = 'success', details: str = None):
    """Log a system operation"""
    operations_log.log_operation('System', operation, status, details)


def log_monitoring(operation: str, status: str = 'success', details: str = None):
    """Log a monitoring operation"""
    operations_log.log_operation('Monitoring', operation, status, details)


if __name__ == '__main__':
    # Test the operations logger
    print("Testing Daily Operations Logger...")
    
    # Log some sample operations
    log_system("Dashboard server started", "success", "Port 5001")
    log_data_fetch("Fetched ICT arrivals", "success", "30 flights retrieved")
    log_data_fetch("Fetched ICT departures", "success", "29 flights retrieved")
    log_backup("Hourly backup created", "success", "68 KB")
    log_monitoring("Health check completed", "success", "All systems operational")
    log_system("Database optimized", "info", "Vacuum completed")
    
    # Get today's operations
    today_ops = operations_log.get_today_operations()
    print(f"\nToday's Operations: {len(today_ops)}")
    
    # Get summary
    summary = operations_log.get_daily_summary()
    print(f"\nDaily Summary:")
    print(f"  Total: {summary['total_operations']}")
    print(f"  By Category: {summary['by_category']}")
    print(f"  By Status: {summary['by_status']}")
    
    print("\nOperations log test complete!")
