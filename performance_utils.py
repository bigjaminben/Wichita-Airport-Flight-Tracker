"""
Performance optimization module for Airport Tracker
Reduces startup time and improves response speed
"""

import functools
import time
from typing import Callable, Any

# Simple in-memory cache decorator
def simple_cache(ttl_seconds: int = 30):
    """
    Simple caching decorator with TTL
    
    Args:
        ttl_seconds: Time to live for cached results
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_time = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}_{args}_{sorted(kwargs.items())}"
            
            # Check if cache is valid
            now = time.time()
            if key in cache and (now - cache_time.get(key, 0)) < ttl_seconds:
                return cache[key]
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = now
            
            return result
        
        return wrapper
    return decorator


def batch_process(items: list, batch_size: int = 100) -> list:
    """
    Process items in batches for better performance
    
    Args:
        items: List of items to process
        batch_size: Size of each batch
        
    Returns:
        List of processed items
    """
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results.extend(batch)
    return results
