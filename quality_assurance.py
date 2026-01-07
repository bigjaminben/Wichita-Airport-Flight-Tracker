"""
Enterprise quality assurance and validation module
Provides comprehensive validation, error checking, and quality metrics
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates data quality and consistency"""
    
    @staticmethod
    def validate_flight_data(flight: Dict[str, Any]) -> bool:
        """
        Validate flight data structure and content
        
        Args:
            flight: Flight dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['Flight_Number', 'Airline', 'Type']
        
        # Check required fields exist
        for field in required_fields:
            if field not in flight or not flight[field]:
                logger.debug(f"Missing required field: {field}")
                return False
        
        # Validate flight type
        if flight['Type'] not in ['Arrival', 'Departure']:
            logger.debug(f"Invalid flight type: {flight.get('Type')}")
            return False
        
        # Validate airline is from approved list (ICT operators only)
        approved_airlines = {
            'Allegiant Air', 'American Airlines', 'Delta Air Lines',
            'Southwest Airlines', 'United Airlines', 'Alpine Air Express'
        }
        
        if flight['Airline'] not in approved_airlines:
            logger.debug(f"Unapproved airline: {flight.get('Airline')}")
            return False
        
        return True
    
    @staticmethod
    def validate_api_response(data: Any, expected_type: type) -> bool:
        """
        Validate API response type
        
        Args:
            data: Response data to validate
            expected_type: Expected Python type
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, expected_type):
            logger.warning(f"Invalid response type. Expected {expected_type}, got {type(data)}")
            return False
        return True
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """
        Sanitize string input
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Remove control characters and trim
        sanitized = ''.join(char for char in value if ord(char) >= 32)
        sanitized = sanitized.strip()
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized


class QualityMetrics:
    """Track and report data quality metrics"""
    
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_errors': 0,
            'data_quality_score': 100.0
        }
    
    def record_request(self, success: bool):
        """Record API request result"""
        self.metrics['total_requests'] += 1
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
        self._update_quality_score()
    
    def record_cache(self, hit: bool):
        """Record cache hit/miss"""
        if hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
    
    def record_validation_error(self):
        """Record data validation error"""
        self.metrics['validation_errors'] += 1
        self._update_quality_score()
    
    def _update_quality_score(self):
        """Calculate overall data quality score (0-100)"""
        total = self.metrics['total_requests']
        if total == 0:
            return
        
        success_rate = (self.metrics['successful_requests'] / total) * 100
        error_penalty = min(self.metrics['validation_errors'] * 2, 50)
        
        self.metrics['data_quality_score'] = max(0, success_rate - error_penalty)
    
    def get_report(self) -> Dict[str, Any]:
        """Get quality metrics report"""
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (
            (self.metrics['cache_hits'] / cache_total * 100)
            if cache_total > 0 else 0
        )
        
        return {
            **self.metrics,
            'cache_hit_rate': round(cache_hit_rate, 2),
            'success_rate': round(
                (self.metrics['successful_requests'] / max(1, self.metrics['total_requests'])) * 100,
                2
            ),
            'timestamp': datetime.now().isoformat()
        }


# Global quality metrics instance
_quality_metrics = QualityMetrics()


def get_quality_metrics() -> QualityMetrics:
    """Get global quality metrics instance"""
    return _quality_metrics
