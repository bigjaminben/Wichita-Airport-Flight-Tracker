"""
Enterprise API Application
Production-ready Flask application with all enterprise features
"""
from flask import Flask, jsonify, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from prometheus_client import make_wsgi_app, Info
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import time
import json
import psutil
import sys

# Enterprise modules
from config import get_settings
from enterprise_logging import setup_logging, add_correlation_id, get_logger, log_request_info, log_response_info
from enterprise_middleware import (
    require_api_key, add_security_headers, track_metrics, handle_errors,
    before_request_middleware, after_request_middleware, record_cache_hit, record_cache_miss
)
from enterprise_weather import get_weather_service
from data_sources import get_aggregator
from redis_cache import get_cache

# Initialize settings
settings = get_settings()

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# CORS configuration
CORS(app, origins=settings.CORS_ORIGINS, supports_credentials=True)

# Rate limiting
if settings.RATE_LIMIT_ENABLED:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        storage_uri=settings.RATE_LIMIT_STORAGE_URL,
        strategy="fixed-window"
    )
    logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_DEFAULT}")
else:
    limiter = None

# Initialize services
aggregator = get_aggregator()
cache = get_cache()
weather_service = get_weather_service()

# Application info metric
app_info = Info('flight_tracker_app', 'Application information')
app_info.info({
    'version': settings.APP_VERSION,
    'environment': settings.ENVIRONMENT,
    'python_version': sys.version
})

# Register error handlers
handle_errors(app)

# Register middleware
@app.before_request
def before_request():
    """Execute before each request"""
    add_correlation_id()
    before_request_middleware()
    log_request_info(logger)


@app.after_request
def after_request(response):
    """Execute after each request"""
    # Add security headers
    response = add_security_headers(response)
    
    # Track metrics
    response = track_metrics(response)
    
    # Log response
    if hasattr(g, 'start_time'):
        duration_ms = (time.time() - g.start_time) * 1000
        log_response_info(logger, response, duration_ms)
    
    response = after_request_middleware(response)
    
    return response


# Health check endpoints (no auth required)
@app.route('/health', methods=['GET'])
def health_check():
    """Kubernetes liveness probe"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': settings.APP_VERSION
    }), 200


@app.route('/ready', methods=['GET'])
def readiness_check():
    """Kubernetes readiness probe"""
    checks = {
        'redis': False,
        'aggregator': False
    }
    
    # Check Redis
    try:
        cache.ping()
        checks['redis'] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
    
    # Check aggregator
    try:
        checks['aggregator'] = aggregator is not None
    except Exception as e:
        logger.error(f"Aggregator health check failed: {e}")
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'ready' if all_healthy else 'not ready',
        'checks': checks,
        'timestamp': time.time()
    }), status_code


@app.route('/info', methods=['GET'])
def app_info_endpoint():
    """Application information"""
    return jsonify({
        'name': settings.APP_NAME,
        'version': settings.APP_VERSION,
        'environment': settings.ENVIRONMENT,
        'python_version': sys.version,
        'features': {
            'rate_limiting': settings.RATE_LIMIT_ENABLED,
            'caching': settings.CACHE_ENABLED,
            'metrics': settings.METRICS_ENABLED,
            'tracing': settings.TRACING_ENABLED
        }
    }), 200


@app.route('/stats', methods=['GET'])
@require_api_key
def system_stats():
    """System resource statistics"""
    return jsonify({
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'process': {
            'cpu_percent': psutil.Process().cpu_percent(),
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'threads': psutil.Process().num_threads()
        },
        'timestamp': time.time()
    }), 200


# API endpoints (require authentication)
@app.route('/api/v1/flights/all', methods=['GET'])
@require_api_key
def get_all_flights():
    """Get all current flights"""
    cache_key = 'flights:all'
    
    # Check cache
    if settings.CACHE_ENABLED:
        cached = cache.get(cache_key)
        if cached:
            record_cache_hit()
            logger.debug("Cache hit for flights")
            return jsonify(cached), 200
        record_cache_miss()
    
    try:
        # Fetch fresh data from Flightradar24 only
        all_flights = aggregator.get_all_flights()
        
        arrivals = [f for f in all_flights if f.get('Type') == 'Arrival']
        departures = [f for f in all_flights if f.get('Type') == 'Departure']
        
        response_data = {
            'flights': all_flights,
            'count': len(all_flights),
            'arrivals_count': len(arrivals),
            'departures_count': len(departures),
            'sources': ['Airportia'],
            'timestamp': time.time(),
            'cached': False
        }
        
        # Cache the response
        if settings.CACHE_ENABLED:
            cache.set(cache_key, response_data, settings.CACHE_TTL)
        
        logger.info(f"Fetched {len(all_flights)} flights")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error("Error fetching flights", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch flights',
            'message': str(e) if settings.DEBUG else 'Internal error',
            'correlation_id': g.correlation_id
        }), 500


@app.route('/api/v1/weather', methods=['GET'])
@require_api_key
def get_weather():
    """Get weather for active airports"""
    cache_key = 'weather:active'
    
    # Check cache
    if settings.CACHE_ENABLED:
        cached = cache.get(cache_key)
        if cached:
            record_cache_hit()
            return jsonify(cached), 200
        record_cache_miss()
    
    try:
        # Get unique airports from current flights
        flights = aggregator.get_all_flights()  # Only Flightradar24
        airports = set()
        
        for flight in flights:
            if flight.get('Type') == 'Arrival' and flight.get('Origin'):
                airports.add(flight['Origin'])
            elif flight.get('Type') == 'Departure' and flight.get('Destination'):
                airports.add(flight['Destination'])
        
        # Always include ICT
        airports.add('ICT')
        
        # Get weather data
        weather_data = weather_service.get_weather(list(airports))
        
        response_data = {
            'weather': weather_data,
            'timestamp': time.time(),
            'cached': False
        }
        
        # Cache the response
        if settings.CACHE_ENABLED:
            cache.set(cache_key, response_data, settings.WEATHER_CACHE_TTL)
        
        logger.info(f"Fetched weather for {len(weather_data)} airports")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error("Error fetching weather", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch weather',
            'message': str(e) if settings.DEBUG else 'Internal error',
            'correlation_id': g.correlation_id
        }), 500


@app.route('/api/v1/flights/history', methods=['GET'])
@require_api_key
def get_flight_history():
    """Get flight history"""
    cache_key = 'flights:history'
    
    # Check cache
    if settings.CACHE_ENABLED:
        cached = cache.get(cache_key)
        if cached:
            record_cache_hit()
            return jsonify(cached), 200
        record_cache_miss()
    
    try:
        flights = aggregator.get_all_flights()  # Only Flightradar24
        
        arrivals = [f for f in flights if f.get('Type') == 'Arrival']
        departures = [f for f in flights if f.get('Type') == 'Departure']
        
        total = len(flights)
        on_time = sum(1 for f in flights if f.get('Status') and 'delay' not in f['Status'].lower())
        
        response_data = {
            'arrivals': arrivals,
            'departures': departures,
            'stats': {
                'total_flights': total,
                'total_arrivals': len(arrivals),
                'total_departures': len(departures),
                'on_time_percentage': round((on_time / total * 100) if total > 0 else 0, 1)
            },
            'timestamp': time.time(),
            'cached': False
        }
        
        # Cache the response
        if settings.CACHE_ENABLED:
            cache.set(cache_key, response_data, settings.CACHE_TTL)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error("Error fetching flight history", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch flight history',
            'message': str(e) if settings.DEBUG else 'Internal error',
            'correlation_id': g.correlation_id
        }), 500


@app.route('/api/v1/predictions/all', methods=['GET'])
@require_api_key
def get_predictions():
    """Get delay predictions (placeholder)"""
    return jsonify({
        'predictions': [],
        'timestamp': time.time(),
        'message': 'ML prediction service coming soon'
    }), 200


# Serve static files
@app.route('/', methods=['GET'])
def serve_dashboard():
    """Serve dashboard"""
    return app.send_static_file('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return app.send_static_file(filename)


# Create metrics endpoint as a route instead of middleware
@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    if settings.ENVIRONMENT == 'production':
        # Use Waitress in production
        from waitress import serve
        logger.info(f"Starting Waitress server on {settings.HOST}:{settings.PORT}")
        serve(app, host=settings.HOST, port=settings.PORT, threads=settings.WORKERS)
    else:
        # Use Flask dev server for development
        logger.warning("Using Flask development server - NOT for production!")
        app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
