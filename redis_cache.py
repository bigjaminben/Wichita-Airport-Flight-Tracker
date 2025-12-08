"""
Redis Cache Manager for Flight Tracker
Provides real-time caching with TTL for high-performance data access
"""

import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import pickle

logger = logging.getLogger(__name__)

class RedisCache:
    """Manages Redis caching for flight data with automatic TTL"""
    
    def __init__(self, host='localhost', port=6379, db=0, ttl=20):
        """
        Initialize Redis cache
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            ttl: Time-to-live in seconds (default 20s for flight data)
        """
        self.ttl = ttl
        self.enabled = False
        
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=False,  # We'll handle encoding
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis.ping()
            self.enabled = True
            logger.info(f"Redis cache connected: {host}:{port} (TTL: {ttl}s)")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None
        
        try:
            value = self.redis.get(key)
            if value:
                # Deserialize with pickle for complex objects
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (can be dict, list, object)
            ttl: Time-to-live in seconds (uses default if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Serialize with pickle to support complex objects
            serialized = pickle.dumps(value)
            expire_time = ttl if ttl is not None else self.ttl
            self.redis.setex(key, expire_time, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False
        
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., 'flights:*')
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear pattern error for '{pattern}': {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.enabled:
            return {'enabled': False}
        
        try:
            info = self.redis.info()
            return {
                'enabled': True,
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_mb': round(info.get('used_memory', 0) / (1024 * 1024), 2),
                'total_keys': self.redis.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'enabled': True, 'error': str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> str:
        """Calculate cache hit rate percentage"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        
        if total == 0:
            return "0%"
        
        rate = (hits / total) * 100
        return f"{rate:.1f}%"
    
    def set_flight_data(self, flight_type: str, data: List[Dict]) -> bool:
        """
        Cache flight data (arrivals or departures)
        
        Args:
            flight_type: 'arrivals' or 'departures'
            data: List of flight dictionaries
            
        Returns:
            True if cached successfully
        """
        key = f"flights:{flight_type}"
        return self.set(key, data)
    
    def get_flight_data(self, flight_type: str) -> Optional[List[Dict]]:
        """
        Get cached flight data
        
        Args:
            flight_type: 'arrivals' or 'departures'
            
        Returns:
            List of flight dictionaries or None if not cached
        """
        key = f"flights:{flight_type}"
        return self.get(key)
    
    def set_aggregated_data(self, data: List[Dict]) -> bool:
        """Cache aggregated flight data from all sources"""
        return self.set("flights:aggregated", data)
    
    def get_aggregated_data(self) -> Optional[List[Dict]]:
        """Get cached aggregated flight data"""
        return self.get("flights:aggregated")
    
    def invalidate_all_flights(self) -> int:
        """Clear all flight-related cache entries"""
        return self.clear_pattern("flights:*")
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self.enabled


# Singleton instance
_cache_instance = None

def get_cache() -> RedisCache:
    """Get singleton Redis cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
