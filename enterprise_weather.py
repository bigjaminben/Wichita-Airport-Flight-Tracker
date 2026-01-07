"""
Enterprise Weather Service
Real weather API integration with circuit breaker, retry logic, and caching
"""
import requests
from typing import Dict, Optional, List
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import get_settings
from enterprise_logging import get_logger
from redis_cache import get_cache

settings = get_settings()
logger = get_logger(__name__)
cache = get_cache()


class WeatherService:
    """Enterprise weather service with failover and resilience"""
    
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.api_url = settings.WEATHER_API_URL
        self.cache_ttl = settings.WEATHER_CACHE_TTL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'{settings.APP_NAME}/{settings.APP_VERSION}'
        })
    
    @circuit(failure_threshold=settings.CIRCUIT_BREAKER_FAIL_MAX, 
             recovery_timeout=settings.CIRCUIT_BREAKER_TIMEOUT_DURATION,
             expected_exception=requests.RequestException)
    @retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(min=settings.RETRY_WAIT_MIN, max=settings.RETRY_WAIT_MAX),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True
    )
    def _fetch_weather_from_api(self, airport_code: str, lat: float, lon: float) -> Optional[Dict]:
        """Fetch weather from OpenWeatherMap API with retry and circuit breaker"""
        
        if not self.api_key:
            logger.warning("Weather API key not configured, using fallback data")
            return None
        
        try:
            url = f"{self.api_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'imperial'
            }
            
            logger.debug(f"Fetching weather for {airport_code}", extra={'lat': lat, 'lon': lon})
            
            response = self.session.get(
                url,
                params=params,
                timeout=settings.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Transform to our format
            weather_data = {
                'Temperature_F': round(data['main']['temp'], 1),
                'Condition': data['weather'][0]['description'].title(),
                'Wind_Speed_mph': round(data['wind']['speed'], 1),
                'Visibility_miles': round(data.get('visibility', 10000) / 1609.34, 1),
                'Humidity_percent': data['main']['humidity'],
                'Pressure_inHg': round(data['main']['pressure'] * 0.02953, 2),
                'Feels_Like_F': round(data['main']['feels_like'], 1),
                'City': data['name']
            }
            
            logger.info(f"Weather fetched successfully for {airport_code}")
            return weather_data
            
        except requests.RequestException as e:
            logger.error(
                f"Weather API request failed for {airport_code}",
                exc_info=True,
                extra={'error': str(e)}
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error fetching weather for {airport_code}",
                exc_info=True
            )
            return None
    
    def get_weather(self, airport_codes: List[str]) -> Dict[str, Dict]:
        """Get weather for multiple airports with caching"""
        
        # Airport coordinates (major US airports)
        AIRPORT_COORDS = {
            'ICT': (37.6499, -97.4331, 'Wichita, KS'),
            'ATL': (33.6407, -84.4277, 'Atlanta, GA'),
            'DFW': (32.8998, -97.0403, 'Dallas-Fort Worth, TX'),
            'ORD': (41.9742, -87.9073, 'Chicago, IL'),
            'DEN': (39.8561, -104.6737, 'Denver, CO'),
            'LAX': (33.9416, -118.4085, 'Los Angeles, CA'),
            'JFK': (40.6413, -73.7781, 'New York, NY'),
            'SFO': (37.6213, -122.3790, 'San Francisco, CA'),
            'LAS': (36.0840, -115.1537, 'Las Vegas, NV'),
            'PHX': (33.4352, -112.0101, 'Phoenix, AZ'),
            'IAH': (29.9902, -95.3368, 'Houston, TX'),
            'MCO': (28.4312, -81.3081, 'Orlando, FL'),
            'SEA': (47.4502, -122.3088, 'Seattle, WA'),
            'MSP': (44.8848, -93.2223, 'Minneapolis, MN'),
            'DTW': (42.2162, -83.3554, 'Detroit, MI'),
            'BOS': (42.3656, -71.0096, 'Boston, MA'),
            'PHL': (39.8729, -75.2437, 'Philadelphia, PA'),
            'LGA': (40.7769, -73.8740, 'New York, NY'),
            'FLL': (26.0742, -80.1506, 'Fort Lauderdale, FL'),
            'BWI': (39.1774, -76.6684, 'Baltimore, MD')
        }
        
        weather_data = {}
        
        for airport_code in airport_codes:
            if airport_code not in AIRPORT_COORDS:
                logger.debug(f"Unknown airport code: {airport_code}")
                continue
            
            # Check cache first
            cache_key = f"weather:{airport_code}"
            cached = cache.get(cache_key)
            
            if cached:
                logger.debug(f"Weather cache hit for {airport_code}")
                weather_data[airport_code] = cached
                continue
            
            # Fetch from API
            lat, lon, city = AIRPORT_COORDS[airport_code]
            
            try:
                data = self._fetch_weather_from_api(airport_code, lat, lon)
                
                if data:
                    data['City'] = city
                    weather_data[airport_code] = data
                    
                    # Cache the result
                    cache.set(cache_key, data, self.cache_ttl)
                else:
                    # Use fallback data
                    weather_data[airport_code] = self._get_fallback_weather(airport_code, city)
                    
            except Exception as e:
                logger.error(f"Failed to get weather for {airport_code}, using fallback")
                weather_data[airport_code] = self._get_fallback_weather(airport_code, city)
        
        return weather_data
    
    def _get_fallback_weather(self, airport_code: str, city: str) -> Dict:
        """Fallback weather data when API is unavailable"""
        
        # Reasonable default values
        fallback_data = {
            'ICT': {'Temperature_F': 38, 'Condition': 'Partly Cloudy', 'Wind_Speed_mph': 12, 'Humidity_percent': 65},
            'ATL': {'Temperature_F': 48, 'Condition': 'Partly Cloudy', 'Wind_Speed_mph': 7, 'Humidity_percent': 60},
            'DFW': {'Temperature_F': 52, 'Condition': 'Clear', 'Wind_Speed_mph': 8, 'Humidity_percent': 55},
            'ORD': {'Temperature_F': 28, 'Condition': 'Cloudy', 'Wind_Speed_mph': 15, 'Humidity_percent': 72},
            'DEN': {'Temperature_F': 42, 'Condition': 'Sunny', 'Wind_Speed_mph': 10, 'Humidity_percent': 35},
            'LAX': {'Temperature_F': 68, 'Condition': 'Sunny', 'Wind_Speed_mph': 8, 'Humidity_percent': 55},
            'PHX': {'Temperature_F': 68, 'Condition': 'Sunny', 'Wind_Speed_mph': 5, 'Humidity_percent': 25},
            'MSP': {'Temperature_F': 22, 'Condition': 'Snow', 'Wind_Speed_mph': 18, 'Humidity_percent': 80}
        }
        
        data = fallback_data.get(airport_code, {
            'Temperature_F': 50,
            'Condition': 'Unknown',
            'Wind_Speed_mph': 10,
            'Humidity_percent': 50
        })
        
        data.update({
            'City': city,
            'Visibility_miles': 10.0,
            'Pressure_inHg': 29.92,
            'Feels_Like_F': data['Temperature_F'],
            'source': 'fallback'
        })
        
        return data


# Singleton instance
_weather_service = None


def get_weather_service() -> WeatherService:
    """Get weather service singleton"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
