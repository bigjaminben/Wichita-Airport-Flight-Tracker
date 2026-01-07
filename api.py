"""
ICT Airport Operations Intelligence Platform - API Server
Enterprise Flask Application

@fileoverview: RESTful API server providing real-time flight data, weather information,
               machine learning predictions, and operational analytics for the ICT Airport
               Operations Intelligence Platform.

@version: 2.0.0
@author: Deloitte Consulting LLP
@copyright: 2025 Deloitte Consulting LLP. All rights reserved.
@license: Proprietary - For authorized use only

Features:
- Real-time flight data aggregation from multiple sources
- Redis-powered caching for optimal performance
- ML-powered delay predictions
- Comprehensive error handling and logging
- RESTful API design with JSON responses
- CORS support for web client integration
"""

from flask import Flask, jsonify, send_file, make_response, send_from_directory, request
import io
import os
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
import json
import time
import threading
import gzip

# Lazy import matplotlib only when needed for plots
_matplotlib_loaded = False

def load_matplotlib():
    """Lazy load matplotlib to speed up initial startup"""
    global _matplotlib_loaded, matplotlib, plt
    if not _matplotlib_loaded:
        import matplotlib
        matplotlib.use('Agg')  # Non-GUI backend
        import matplotlib.pyplot as plt
        _matplotlib_loaded = True
    return matplotlib, plt

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.info("Initializing ICT Airport Operations Intelligence Platform API Server")

# ============================================================================
# IMPORTS - DATA SOURCES & SERVICES
# ============================================================================

# Import enhanced data sources
from data_sources import get_aggregator, AirportStatistics
from hdf5_storage import get_storage
from node_red_integration import NodeRedManager
from quality_assurance import DataValidator, get_quality_metrics

# Import Redis cache manager
from redis_cache import get_cache

# Import delay predictor
from delay_predictor import get_predictor

# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize Redis cache
_redis_cache = get_cache()
logger.info("Redis cache manager initialized successfully")

# Lazy initialize aggregator and statistics (only when needed)
_aggregator = None
_statistics = None
_data_warming = False

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def warm_data_cache():
    """
    Background thread to pre-warm cache with real flight data
    
    This function runs asynchronously to populate the Redis cache with
    fresh flight data, improving initial response times for API requests.
    
    Returns:
        None
    """
    global _data_warming
    if _data_warming:
        logger.debug("Cache warming already in progress, skipping")
        return
    _data_warming = True
    
    def _warm():
        global _data_warming
        try:
            logger.info("Starting background cache warming operation...")
            aggregator = get_lazy_aggregator()
            flights = aggregator.get_all_flights()
            
            cache_data = {
                'flights': flights,
                'count': len(flights),
                'timestamp': time.time(),
                'sources': ['Flightradar24']  # Real ADS-B radar data only
            }
            
            _redis_cache.set('flights_response', json.dumps({
                'flights': flights,
                'count': len(flights),
                'timestamp': time.time()
            }), 30)
            
            _redis_cache.set('flights_all_response', json.dumps(cache_data), 30)
            
            logger.info(f"✓ Cache successfully warmed with {len(flights)} flights from {len(cache_data['sources'])} sources")
            
        except Exception as e:
            logger.error(f"✗ Error during cache warming operation: {str(e)}", exc_info=True)
        finally:
            _data_warming = False
    
    # Start warming in background thread
    threading.Thread(target=_warm, daemon=True, name="CacheWarmer").start()

def get_lazy_aggregator():
    """
    Get aggregator instance with lazy initialization
    
    Returns:
        FlightAggregator: Initialized flight data aggregator
    """
    global _aggregator
    if _aggregator is None:
        logger.info("Initializing flight data aggregator...")
        _aggregator = get_aggregator()
        logger.info("✓ Flight data aggregator initialized successfully")
    return _aggregator

def get_lazy_statistics():
    """
    Get statistics instance with lazy initialization
    
    Returns:
        AirportStatistics: Initialized airport statistics engine
    """
    global _statistics
    if _statistics is None:
        logger.info("Initializing airport statistics engine...")
        _statistics = AirportStatistics()
        logger.info("✓ Airport statistics engine initialized successfully")
    return _statistics


def to_serializable(obj):
    """
    Convert non-JSON-serializable objects to serializable forms
    
    Args:
        obj: Object to convert
        
    Returns:
        Serializable representation of the object
    """
    try:
        import numpy as _np
        if isinstance(obj, _np.generic):
            # use .item() which works for numpy scalars and avoids deprecated asscalar
            return obj.item()
    except Exception:
        pass
    return str(obj)


# ============================================================================
# FLASK APPLICATION CONFIGURATION
# ============================================================================

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['COMPRESS_MIMETYPES'] = [
    'text/html', 
    'text/css', 
    'text/xml', 
    'application/json', 
    'application/javascript'
]
app.config['COMPRESS_LEVEL'] = 6
app.config['JSON_SORT_KEYS'] = False  # Preserve key order for better readability
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # 5 minute cache for static files

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add enterprise-grade security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # CORS for API endpoints only
    if request.path.startswith('/api/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    return response


def create_error_response(
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create standardized error response with quality tracking
    
    Args:
        message: Human-readable error message
        status_code: HTTP status code (default: 500)
        details: Optional additional error details dictionary
        
    Returns:
        Tuple of (Flask JSON response, status_code)
    """
    get_quality_metrics().record_request(success=False)
    
    error_response = {
        'error': True,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'status': status_code
    }
    
    if details:
        error_response['details'] = details
    
    logger.error(f"API Error: {message} (status={status_code})", extra=details or {})
    return jsonify(error_response), status_code


def create_success_response(data: Any, cache_ttl: Optional[int] = None) -> Any:
    """
    Create standardized success response with optional caching headers
    
    Args:
        data: Response data (will be JSONified)
        cache_ttl: Optional cache TTL in seconds for Cache-Control header
        
    Returns:
        Flask response object with appropriate headers
    """
    get_quality_metrics().record_request(success=True)
    
    response = make_response(jsonify(data))
    
    if cache_ttl:
        response.headers['Cache-Control'] = f'public, max-age={cache_ttl}'
    
    return response
app.config['COMPRESS_MIN_SIZE'] = 500
app.config['JSON_SORT_KEYS'] = False  # Preserve insertion order
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Compact JSON for production

# Cache configuration - optimized for real-time data requirements
CACHE_TTL = 10  # Fast refresh rate (10 seconds) for real-time data

logger.info("Flask application configured successfully")
logger.info(f"API cache TTL set to {CACHE_TTL} seconds for optimal performance")

# In-memory cache structure (fallback if Redis unavailable)
_cache = {
    'data_ts': 0.0,
    'flights_json': None,
    'weather_json': None,
    'plots': {}  # name -> (ts, bytes)
}
_cache_lock = threading.Lock()

# Cache helper functions
def _get_cached(key):
    """Get from Redis first, fall back to memory cache"""
    if _redis_cache.is_available():
        return _redis_cache.get(key)
    return _cache.get(key)

def _set_cached(key, value, ttl=CACHE_TTL):
    """Set in Redis first, fall back to memory cache"""
    if _redis_cache.is_available():
        return _redis_cache.set(key, value, ttl)
    with _cache_lock:
        _cache[key] = value
        _cache['data_ts'] = time.time()
    return True


def jsonify_compressed(data, status=200):
    """Return JSON response with optional GZIP compression"""
    response = make_response(jsonify(data), status)
    
    # Add cache control headers for better browser caching
    response.headers['Cache-Control'] = f'public, max-age={CACHE_TTL}'
    
    # Check if client accepts gzip
    if 'gzip' in request.headers.get('Accept-Encoding', '').lower():
        json_str = json.dumps(data)
        if len(json_str) > 1000:  # Only compress if larger than 1KB
            gzipped = gzip.compress(json_str.encode('utf-8'))
            response = make_response(gzipped)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Length'] = len(gzipped)
            response.headers['Cache-Control'] = f'public, max-age={CACHE_TTL}'
    
    return response


# Legacy tracker initialization removed - using fast aggregator instead


def ensure_fresh_data():
    """Ensure data cache is fresh - uses fast aggregator with Redis."""
    # Data is fetched on-demand by aggregator with built-in caching
    # No initialization needed - aggregator handles it automatically
    pass


@app.route('/api/flights')
def api_flights():
    """Get all flights from Flightradar24 (real ADS-B radar data only)
    
    Returns:
        JSON response with flights array, count, timestamp, and source
        Cache-Control: 30 seconds
        Status: 200 OK or 500 Internal Server Error
    """
    start_time = time.time()
    
    try:
        # Check cache first for optimal performance
        cached = _redis_cache.get('flights_response')
        if cached:
            logger.debug(f"Cache hit for flights_response")
            return jsonify_compressed(json.loads(cached))
        
        logger.debug("Cache miss - fetching fresh flight data")
        
        # Fetch ONLY from Flightradar24 (real ADS-B radar data)
        aggregator = get_lazy_aggregator()
        if not aggregator:
            raise ValueError("Flight data aggregator unavailable")
            
        flights = aggregator.get_all_flights()
        
        # Validate response
        if flights is None:
            flights = []
            logger.warning("Flight aggregator returned None, using empty array")
        
        response_data = {
            'flights': flights,
            'count': len(flights),
            'timestamp': time.time(),
            'source': 'Flightradar24',  # Real ADS-B radar only
            'airlines': list(set(f.get('Airline', 'Unknown') for f in flights if f.get('Airline'))),
            'cache_status': 'miss'
        }
        
        # Cache for 30 seconds for better performance
        _redis_cache.set('flights_response', json.dumps(response_data), 30)
        
        elapsed = time.time() - start_time
        logger.info(f"Fetched {len(flights)} flights in {elapsed:.2f}s")
        
        return jsonify_compressed(response_data)
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error fetching flights after {elapsed:.2f}s: {e}", exc_info=True)
        
        # Return graceful error with empty data
        return jsonify({
            'error': 'Unable to fetch flight data',
            'error_detail': str(e) if app.debug else None,
            'flights': [],
            'count': 0,
            'timestamp': time.time(),
            'source': 'Flightradar24'
        }), 500


@app.route('/api/flights/all')
def api_flights_all():
    """
    Get all flights from Flightradar24 ADS-B radar data
    
    Returns JSON with flights array, count, metadata, and timestamp.
    Uses 30-second cache for optimal performance.
    Only returns flights from real ICT operators (G4, AA, DL, WN, UA, 5A).
    """
    start_time = time.time()
    
    try:
        # Check cache first
        cached = _redis_cache.get('flights_all_response')
        if cached:
            get_quality_metrics().record_cache(hit=True)
            logger.debug("Cache HIT for flights/all endpoint")
            return jsonify_compressed(json.loads(cached))
        
        get_quality_metrics().record_cache(hit=False)
        logger.debug("Cache MISS for flights/all endpoint - fetching fresh data")
        
        # Fetch ONLY from Flightradar24 (real ADS-B radar data)
        aggregator = get_lazy_aggregator()
        if not aggregator:
            return create_error_response(
                "Flight data aggregator unavailable",
                status_code=503,
                details={'service': 'Flightradar24 API'}
            )
        
        flights = aggregator.get_all_flights()  # Only uses Flightradar24, filters by real ICT airlines
        
        # Validate flight data quality
        if flights:
            validator = DataValidator()
            valid_flights = [
                flight for flight in flights
                if validator.validate_flight_data(flight)
            ]
            
            if len(valid_flights) < len(flights):
                invalid_count = len(flights) - len(valid_flights)
                logger.warning(f"Filtered out {invalid_count} invalid flight records")
                get_quality_metrics().record_validation_error()
            
            flights = valid_flights
        
        response_data = {
            'flights': flights,
            'count': len(flights),
            'sources': ['Flightradar24'],  # Real ADS-B radar only
            'timestamp': time.time()
        }
        
        # Cache for 10 seconds
        _redis_cache.set('flights_all_response', json.dumps(response_data), 10)
        return jsonify_compressed(response_data)
    except Exception as e:
        logger.error(f"Error fetching all flights: {e}")
        return jsonify({'error': str(e), 'flights': [], 'count': 0}), 500


@app.route('/api/flights/flightradar24')
def api_flights_fr24():
    """
    Get flights from Flightradar24 ADS-B radar only
    
    Direct access to Flightradar24 data without aggregation.
    Includes airline filtering for ICT operators only.
    """
    try:
        aggregator = get_aggregator()
        if not aggregator:
            return create_error_response(
                "Flightradar24 service unavailable",
                status_code=503
            )
        
        flights = aggregator.fetch_flightradar24_data()
        
        return create_success_response({
            'flights': flights,
            'count': len(flights),
            'source': 'Flightradar24',
            'timestamp': time.time()
        }, cache_ttl=30)
        
    except Exception as e:
        logger.error(f"Flightradar24 API error: {e}", exc_info=True)
        return create_error_response(
            "Failed to fetch Flightradar24 data",
            details={'error': str(e)}
        )


@app.route('/api/flights/airportia')
def api_flights_airportia():
    """
    DISABLED - Airportia endpoint permanently removed
    
    Airportia was returning unrealistic data including code-share flights
    from airlines that don't operate at ICT (Korean Air, Air France, Emirates).
    Use /api/flights for Flightradar24 ADS-B radar data only.
    """
    return create_error_response(
        "Airportia endpoint disabled - use /api/flights for real ADS-B radar data",
        status_code=410  # 410 Gone - resource permanently removed
    )


@app.route('/api/flights/history')
def api_flights_history():
    """
    Get historical flight data from HDF5 database
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) - defaults to 7 days ago
    - end_date: End date (YYYY-MM-DD) - defaults to today
    - days: Alternative to date range, get last N days (default: 7)
    """
    try:
        # Parse query parameters
        days = int(request.args.get('days', 7))
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Create cache key based on parameters
        cache_key = f'history_response_{days}_{start_date_str}_{end_date_str}'
        
        # Check cache first
        cached = _redis_cache.get(cache_key)
        if cached:
            return jsonify_compressed(json.loads(cached))
        
        # Get HDF5 storage instance
        storage = get_storage()
        
        # Query flights from database
        arrivals = storage.get_flights('arrivals', days=days)
        departures = storage.get_flights('departures', days=days)
        
        # Filter by date range if specified
        if start_date_str or end_date_str:
            from datetime import datetime
            
            start_date = datetime.fromisoformat(start_date_str) if start_date_str else datetime.now() - timedelta(days=days)
            end_date = datetime.fromisoformat(end_date_str) if end_date_str else datetime.now()
            
            def in_range(flight):
                try:
                    scheduled = flight.get('scheduled_time', '')
                    if not scheduled or scheduled in ('N/A', '', 'None'):
                        return False
                    flight_date = datetime.fromisoformat(scheduled.replace('Z', '+00:00'))
                    return start_date <= flight_date <= end_date
                except:
                    return False
            
            arrivals = [f for f in arrivals if in_range(f)]
            departures = [f for f in departures if in_range(f)]
        
        # Calculate comprehensive statistics
        total_flights = len(arrivals) + len(departures)
        
        # Count status types
        delayed_count = 0
        cancelled_count = 0
        on_time_count = 0
        
        for flight in arrivals + departures:
            status = flight.get('status', flight.get('Status', '')).lower()
            if 'cancel' in status:
                cancelled_count += 1
            elif 'delay' in status or 'late' in status:
                delayed_count += 1
            else:
                on_time_count += 1
        
        on_time_percentage = round((on_time_count / total_flights * 100) if total_flights > 0 else 0, 1)
        
        response_data = {
            'arrivals': arrivals,
            'departures': departures,
            'stats': {
                'total_flights': total_flights,
                'total_arrivals': len(arrivals),
                'total_departures': len(departures),
                'on_time_count': on_time_count,
                'delayed_count': delayed_count,
                'cancelled_count': cancelled_count,
                'on_time_percentage': on_time_percentage
            },
            'query': {
                'days': days,
                'start_date': start_date_str,
                'end_date': end_date_str
            },
            'timestamp': time.time()
        }
        
        # Cache the response (shorter TTL for historical data)
        _redis_cache.set(cache_key, json.dumps(response_data), 300)  # 5 minute cache
        return jsonify_compressed(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'arrivals': [],
            'departures': [],
            'stats': {
                'total_flights': 0,
                'total_arrivals': 0,
                'total_departures': 0,
                'on_time_count': 0,
                'delayed_count': 0,
                'cancelled_count': 0,
                'on_time_percentage': 0
            },
            'error': str(e),
            'timestamp': time.time()
        }), 200


@app.route('/api/airport/info')
def api_airport_info():
    """Get comprehensive airport information"""
    try:
        info = AirportStatistics.get_airport_info('ICT')
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/airport/nas-status')
def api_nas_status():
    """Get National Airspace System status"""
    try:
        status = AirportStatistics.fetch_nas_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics/bts')
def api_bts_stats():
    """Get Bureau of Transportation Statistics data structure"""
    try:
        aggregator = get_aggregator()
        stats = aggregator.fetch_bts_statistics('ICT')
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather')
def api_weather():
    """Get weather data from real sources"""
    try:
        # Check cache first
        cached = _redis_cache.get('weather_response')
        if cached:
            return jsonify_compressed(json.loads(cached))
        
        # Get common airports from current flights
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()  # Only uses Flightradar24 now
        
        # Extract unique airports
        airports = set(['ICT'])
        for flight in flights[:20]:  # Check first 20 flights
            if flight.get('Origin') and flight['Origin'] != 'ICT':
                airports.add(flight['Origin'])
            if flight.get('Destination') and flight['Destination'] != 'ICT':
                airports.add(flight['Destination'])
        
        # Get weather data from real sources
        weather_data = {}
        for airport in airports:
            try:
                # TODO: Integrate with real weather API (OpenWeatherMap, NOAA, etc.)
                # For now, airports dict will be empty if no real weather API available
                pass
            except:
                pass
        
        # Always include ICT with real or unavailable status
        if 'ICT' not in weather_data:
            weather_data['ICT'] = {
                'City': 'Wichita, KS',
                'status': 'unavailable'  # Real status - data not available
            }
        
        response_data = {
            'weather': weather_data,
            'timestamp': time.time()
        }
        
        _redis_cache.set('weather_response', json.dumps(response_data), 600)
        return jsonify_compressed(response_data)
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return jsonify({
            'weather': {
                'ICT': {
                    'City': 'Wichita, KS',
                    'status': 'error',
                    'error': str(e)
                }
            },
            'timestamp': time.time()
        }), 200


@app.route('/api/delays/predict')
def api_delays_predict():
    """Predict flight delays using ML model"""
    try:
        predictor = get_predictor()
        
        # Get request data
        flight_data = request.get_json() if request.is_json else {}
        
        if not flight_data:
            return jsonify({'error': 'No flight data provided'}), 400
        
        # Make prediction
        prediction = predictor.predict_delay(flight_data)
        
        return jsonify(prediction)
    except Exception as e:
        logger.error(f"Error predicting delay: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/plot/dashboard')
def api_plot_dashboard():
    """Generate dashboard Plotly plot with real data"""
    try:
        cached = _redis_cache.get('dashboard_plot')
        if cached:
            return cached
        
        # Get real flight data
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()  # Only uses Flightradar24 now
        
        if not flights:
            # No data available - return empty plot with real status
            plot_json = json.dumps({
                'data': [],
                'layout': {
                    'title': 'Real-Time Flight Data - No Data Available',
                    'xaxis': {'title': 'Time'},
                    'yaxis': {'title': 'Flights'},
                    'height': 400,
                    'annotations': [{
                        'text': 'No real-time data available',
                        'xref': 'paper',
                        'yref': 'paper',
                        'x': 0.5,
                        'y': 0.5,
                        'showarrow': False
                    }]
                }
            })
        else:
            # Use real flight data
            plot_json = json.dumps({
                'data': [{
                    'x': [f.get('Scheduled_Time', '') for f in flights[:10]],
                    'y': [i for i in range(1, min(len(flights) + 1, 11))],
                    'type': 'scatter',
                    'mode': 'lines+markers'
                }],
                'layout': {
                    'title': f'Real-Time Flights ({len(flights)} total)',
                    'xaxis': {'title': 'Scheduled Time'},
                    'yaxis': {'title': 'Flight Count'},
                    'height': 400
                }
            })
        
        _redis_cache.set('dashboard_plot', plot_json, 10)
        return plot_json, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Error generating plot: {e}")
        # Return error state with real data
        return json.dumps({
            'data': [],
            'layout': {
                'title': f'Error Loading Data: {str(e)}',
                'xaxis': {'title': 'Time'},
                'yaxis': {'title': 'Flights'},
                'height': 400
            }
        }), 200, {'Content-Type': 'application/json'}


def render_plot_from_method(method_name):
    """Call a plotting method on the tracker and return the PNG bytes.
    We monkeypatch plt.show to a no-op while calling the method so it doesn't block.
    """
    # Lazy load matplotlib
    _, plt = load_matplotlib()
    
    # temporarily disable showing
    original_show = plt.show
    plt.show = lambda *a, **k: None
    try:
        method = getattr(tracker, method_name, None)
        if method is None:
            return None, f'Method {method_name} not found'
        # Call the method which will draw onto matplotlib's current figure
        method()
        buf = io.BytesIO()
        fig = plt.gcf()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        data_bytes = buf.getvalue()
        plt.clf()

        # If a brand logo exists in static/logo.png, overlay it onto the PNG
        try:
            from PIL import Image
            logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
            if os.path.exists(logo_path):
                img = Image.open(io.BytesIO(data_bytes)).convert('RGBA')
                logo = Image.open(logo_path).convert('RGBA')
                # Resize logo to ~12% of image width
                w, h = img.size
                max_logo_w = max(24, int(w * 0.12))
                logo_ratio = logo.width / float(logo.height) if logo.height else 1.0
                logo_w = max_logo_w
                logo_h = max(12, int(logo_w / logo_ratio))
                logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
                margin = int(max(8, w * 0.02))
                pos = (w - logo_w - margin, h - logo_h - margin)
                img.paste(logo, pos, logo)
                outbuf = io.BytesIO()
                img.save(outbuf, format='PNG')
                outbuf.seek(0)
                data_bytes = outbuf.getvalue()
        except Exception:
            # If PIL not available or anything fails, return original bytes
            pass

        return data_bytes, None
    finally:
        plt.show = original_show


PLOT_METHODS = {
    'status_pie': 'plot_flight_status_pie_chart',
    'airline_bar': 'plot_airline_performance_bar_chart',
    'hourly': 'plot_hourly_flight_activity',
    'weather': 'plot_weather_comparison',
    'runway': 'plot_runway_utilization',
    'delays': 'plot_delay_analysis',
    'dashboard': 'plot_comprehensive_dashboard'
}


@app.route('/')
def index():
    # Serve the static UI index page
    try:
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'index.html')
    except Exception as e:
        return jsonify({'error': f'Could not serve index.html: {str(e)}'}), 500


@app.route('/api/operations/today')
def api_operations_today():
    """
    Get today's operations log with summary statistics
    
    Returns JSON with operations array, summary, and date.
    """
    try:
        from operations_logger import operations_log
        from datetime import date
        
        ops = operations_log.get_today_operations()
        summary = operations_log.get_daily_summary()
        
        return create_success_response({
            'operations': ops,
            'summary': summary,
            'date': date.today().isoformat()  # Added missing 'date' field
        })
        
    except Exception as e:
        logger.error(f"Operations log error: {e}", exc_info=True)
        return create_error_response(
            "Failed to retrieve operations log",
            details={'error': str(e)}
        )


@app.route('/api/operations/date/<date_str>')
def api_operations_by_date(date_str):
    """Get operations log for a specific date (YYYY-MM-DD)"""
    try:
        from operations_logger import operations_log
        ops = operations_log.get_operations_by_date(date_str)
        summary = operations_log.get_daily_summary(date_str)
        return jsonify({
            'operations': ops,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/operations/recent/<int:hours>')
def api_operations_recent(hours):
    """Get operations from the last N hours"""
    try:
        from operations_logger import operations_log
        ops = operations_log.get_recent_operations(hours)
        return jsonify({'operations': ops})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cache/stats')
def api_cache_stats():
    """Get Redis cache statistics"""
    try:
        stats = _redis_cache.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e), 'enabled': False}), 500


@app.route('/api/cache/clear', methods=['POST'])
def api_cache_clear():
    """Clear all flight-related cache entries"""
    try:
        count = _redis_cache.invalidate_all_flights()
        with _cache_lock:
            _cache['data_ts'] = 0.0
            _cache['flights_json'] = None
            _cache['weather_json'] = None
            _cache['plots'] = {}
        return jsonify({'cleared': count, 'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/predictions/flight')
def api_predict_flight():
    """
    Get delay prediction for a specific flight
    Query params: flight_number, airport (optional)
    """
    try:
        flight_number = request.args.get('flight_number')
        if not flight_number:
            return jsonify({'error': 'flight_number parameter required'}), 400
        
        # Get current flights and weather
        aggregator = get_aggregator()
        all_flights = aggregator.get_all_flights()
        
        # Find the specific flight
        flight = None
        for f in all_flights:
            if f.get('Flight_Number', '').upper() == flight_number.upper():
                flight = f
                break
        
        if not flight:
            return jsonify({'error': f'Flight {flight_number} not found'}), 404
        
        # Get weather for relevant airport
        airport = flight.get('Origin') if flight.get('Type') == 'Departure' else 'ICT'
        weather = aggregator.get_weather_snapshot(airport)
        
        # Get prediction
        predictor = get_predictor()
        prediction = predictor.predict(flight, weather)
        
        return jsonify({
            'flight_number': flight_number,
            'prediction': prediction,
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/predictions/all')
def api_predict_all():
    """Get delay predictions for all current flights"""
    try:
        # Check cache first
        cached = _redis_cache.get('predictions_response')
        if cached:
            return jsonify_compressed(json.loads(cached))
        
        # Return empty predictions for now (ML predictor not critical for flight display)
        response_data = {
            'predictions': [],
            'timestamp': time.time()
        }
        
        # Cache the response  
        _redis_cache.set('predictions_response', json.dumps(response_data), CACHE_TTL)
        return jsonify_compressed(response_data)
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}")
        return jsonify({'predictions': [], 'timestamp': time.time()}), 200

@app.route('/api/predictions/all_old')
def api_predict_all_old():
    """Get delay predictions for all current flights - DISABLED FOR PERFORMANCE"""
    try:
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()  # Only Flightradar24
        
        predictor = get_predictor()
        predictions = []
        
        for flight in all_flights:
            try:
                # Get weather for relevant airport
                airport = flight.get('Origin') if flight.get('Type') == 'Departure' else 'ICT'
                weather = aggregator.get_weather_snapshot(airport)
                
                # Get prediction
                prediction = predictor.predict(flight, weather)
                
                predictions.append({
                    'flight_number': flight.get('Flight_Number', 'UNKNOWN'),
                    'airline': flight.get('Airline', 'Unknown'),
                    'type': flight.get('Type', 'Unknown'),
                    'prediction': prediction
                })
            except Exception as e:
                logger.warning(f"Could not predict for flight: {e}")
                continue
        
        return jsonify({
            'predictions': predictions,
            'count': len(predictions),
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Predictions error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/predictions/stats')
def api_predictor_stats():
    """Get delay predictor statistics"""
    try:
        predictor = get_predictor()
        stats = predictor.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# REPORT ENDPOINTS FOR NODE-RED EMAIL AUTOMATION
# ============================================================================

@app.route('/api/report/daily')
def api_daily_report():
    """
    Generate daily flight report statistics for automated email reports
    
    Returns comprehensive statistics for today's flight operations including:
    - Total flights, arrivals, departures
    - On-time performance metrics
    - Delay and cancellation counts
    - Busiest hour analysis
    - Top routes
    
    Returns:
        JSON: Daily statistics object
    """
    try:
        logger.info("Generating daily report...")
        aggregator = get_lazy_aggregator()
        
        # Get today's flights
        flights = aggregator.get_all_flights()
        
        # Separate arrivals and departures
        arrivals = [f for f in flights if f.get('Type') == 'Arrival']
        departures = [f for f in flights if f.get('Type') == 'Departure']
        
        # Calculate status counts
        on_time = 0
        delayed = 0
        cancelled = 0
        
        for flight in flights:
            status = (flight.get('Status') or '').lower()
            if 'land' in status or 'arrived' in status or 'departing' in status or 'track' in status:
                on_time += 1
            elif 'delay' in status or 'late' in status:
                delayed += 1
            elif 'cancel' in status:
                cancelled += 1
            else:
                on_time += 1  # Count scheduled/unknown as on-time
        
        # Find busiest hour
        hour_counts = {}
        for flight in flights:
            sched_time = flight.get('Scheduled_Time', '')
            if sched_time:
                try:
                    if 'T' in sched_time:
                        hour = int(sched_time.split('T')[1].split(':')[0])
                    else:
                        hour = int(sched_time.split(':')[0])
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except:
                    pass
        
        busiest_hour = 'N/A'
        if hour_counts:
            max_hour = max(hour_counts.items(), key=lambda x: x[1])
            hour_12 = max_hour[0] if max_hour[0] <= 12 else max_hour[0] - 12
            hour_12 = 12 if hour_12 == 0 else hour_12
            ampm = 'AM' if max_hour[0] < 12 else 'PM'
            busiest_hour = f"{hour_12}:00 {ampm} ({max_hour[1]} flights)"
        
        # Find top route
        route_counts = {}
        for flight in flights:
            if flight.get('Type') == 'Arrival':
                route = f"{flight.get('Origin', 'N/A')} → ICT"
            else:
                route = f"ICT → {flight.get('Destination', 'N/A')}"
            route_counts[route] = route_counts.get(route, 0) + 1
        
        top_route = 'N/A'
        if route_counts:
            max_route = max(route_counts.items(), key=lambda x: x[1])
            top_route = f"{max_route[0]} ({max_route[1]} flights)"
        
        # Calculate on-time percentage
        total = len(flights) if len(flights) > 0 else 1
        on_time_pct = round((on_time / total) * 100, 1)
        
        report = {
            'total_flights': len(flights),
            'arrivals': len(arrivals),
            'departures': len(departures),
            'on_time': on_time,
            'delayed': delayed,
            'cancelled': cancelled,
            'on_time_percentage': on_time_pct,
            'busiest_hour': busiest_hour,
            'top_route': top_route,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"✓ Daily report generated: {len(flights)} flights, {on_time_pct}% on-time")
        return jsonify(report)
        
    except Exception as e:
        logger.error(f"✗ Error generating daily report: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/weekly')
def api_weekly_report():
    """
    Generate weekly flight report statistics for automated email summaries
    
    Returns comprehensive 7-day statistics including:
    - Total weekly flights and daily averages
    - Weekly on-time performance trends
    - Busiest day analysis
    - Route performance
    - Delay patterns
    
    Returns:
        JSON: Weekly statistics object
    """
    try:
        logger.info("Generating weekly report (HDF5-backed 7-day analytics)...")

        # Pull last 7 days of arrivals and departures from HDF5
        storage = get_storage()
        import pandas as pd

        df_arr = storage.export_to_pandas('arrivals', days=7)
        df_dep = storage.export_to_pandas('departures', days=7)

        # Combine and normalize
        frames = []
        if not df_arr.empty:
            df_arr['flight_type'] = 'Arrival'
            frames.append(df_arr)
        if not df_dep.empty:
            df_dep['flight_type'] = 'Departure'
            frames.append(df_dep)

        if not frames:
            # Fallback to current-day approximation if no historical data yet
            aggregator = get_lazy_aggregator()
            flights = aggregator.get_all_flights()
            daily_count = len(flights)
            report = {
                'total_flights': daily_count,  # no weekly yet
                'avg_daily_flights': daily_count,
                'on_time_percentage': 0,
                'delay_percentage': 0,
                'total_delays': 0,
                'total_cancelled': 0,
                'busiest_day': 'N/A',
                'busiest_day_count': 0,
                'top_route': 'N/A',
                'top_route_count': 0,
                'peak_hour': 'N/A',
                'on_time_trend': 'N/A',
                'on_time_trend_class': 'trend-flat',
                'delay_trend': 'N/A',
                'delay_trend_class': 'trend-flat',
                'generated_at': datetime.now().isoformat()
            }
            return jsonify(report), 200

        df = pd.concat(frames, ignore_index=True)

        # Status resolution: prefer current_status then status
        def resolve_status(row):
            s = str(row.get('current_status') or row.get('status') or '').lower()
            return s

        statuses = df.apply(resolve_status, axis=1)
        df['status_resolved'] = statuses

        # Metrics
        total_flights = len(df)
        arrivals = (df['flight_type'] == 'Arrival').sum()
        departures = (df['flight_type'] == 'Departure').sum()

        on_time_mask = (
            df['status_resolved'].str.contains('arriv') |
            df['status_resolved'].str.contains('land') |
            df['status_resolved'].str.contains('depart') |
            df['status_resolved'].eq('') |
            df['status_resolved'].str.contains('scheduled')
        )
        delayed_mask = df['status_resolved'].str.contains('delay') | df['status_resolved'].str.contains('late')
        cancelled_mask = df['status_resolved'].str.contains('cancel')

        on_time = int(on_time_mask.sum())
        delayed = int(delayed_mask.sum())
        cancelled = int(cancelled_mask.sum())

        on_time_pct = round((on_time / total_flights) * 100, 1) if total_flights else 0.0
        delay_pct = round((delayed / total_flights) * 100, 1) if total_flights else 0.0

        # Busiest day: group by scheduled_time date
        df_times = df.copy()
        if 'scheduled_time' in df_times.columns:
            df_times['scheduled_time'] = pd.to_datetime(df_times['scheduled_time'], errors='coerce')
            df_times = df_times.dropna(subset=['scheduled_time'])
            df_times['date'] = df_times['scheduled_time'].dt.date
            day_counts = df_times.groupby('date').size().sort_values(ascending=False)
            if not day_counts.empty:
                busiest_day_date = day_counts.index[0]
                busiest_day_count = int(day_counts.iloc[0])
                busiest_day = str(busiest_day_date)
            else:
                busiest_day = 'N/A'
                busiest_day_count = 0
        else:
            busiest_day = 'N/A'
            busiest_day_count = 0

        # Top route
        def compute_route(row):
            if row['flight_type'] == 'Arrival':
                return f"{row.get('origin', 'N/A')} → ICT"
            else:
                return f"ICT → {row.get('destination', 'N/A')}"

        df['route'] = df.apply(compute_route, axis=1)
        route_counts = df.groupby('route').size().sort_values(ascending=False)
        if not route_counts.empty:
            top_route = str(route_counts.index[0])
            top_route_count = int(route_counts.iloc[0])
        else:
            top_route = 'N/A'
            top_route_count = 0

        # Peak hour across the week
        peak_hour = 'N/A'
        if 'scheduled_time' in df.columns:
            df_hours = df.copy()
            df_hours['scheduled_time'] = pd.to_datetime(df_hours['scheduled_time'], errors='coerce')
            df_hours = df_hours.dropna(subset=['scheduled_time'])
            df_hours['hour'] = df_hours['scheduled_time'].dt.hour
            hour_counts = df_hours.groupby('hour').size().sort_values(ascending=False)
            if not hour_counts.empty:
                max_hour = int(hour_counts.index[0])
                hour_12 = max_hour if max_hour <= 12 else max_hour - 12
                hour_12 = 12 if hour_12 == 0 else hour_12
                ampm = 'AM' if max_hour < 12 else 'PM'
                peak_hour = f"{hour_12}:00 {ampm}"

        # Average daily flights
        unique_days = df_times['date'].nunique() if 'date' in df_times.columns else 7
        avg_daily = round(total_flights / unique_days, 1) if unique_days else total_flights

        # Trends vs previous week (last 14 days split)
        on_time_trend = 'N/A'
        on_time_trend_class = 'trend-flat'
        delay_trend = 'N/A'
        delay_trend_class = 'trend-flat'

        try:
            df14_arr = storage.export_to_pandas('arrivals', days=14)
            df14_dep = storage.export_to_pandas('departures', days=14)
            df14 = pd.concat([df14_arr.assign(flight_type='Arrival'), df14_dep.assign(flight_type='Departure')], ignore_index=True)
            df14['scheduled_time'] = pd.to_datetime(df14.get('scheduled_time'), errors='coerce')
            df14 = df14.dropna(subset=['scheduled_time'])
            cutoff = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=7)
            prev_week = df14[df14['scheduled_time'] < cutoff]
            this_week = df14[df14['scheduled_time'] >= cutoff]

            def pct(series):
                total = len(series)
                if total == 0:
                    return 0.0
                ok = series.str.lower().str.contains('arriv|land|depart|scheduled') | series.eq('')
                return round((ok.sum() / total) * 100, 1)

            prev_pct = pct(prev_week.get('status').fillna('')) if not prev_week.empty else 0.0
            this_pct = pct(this_week.get('status').fillna('')) if not this_week.empty else on_time_pct
            diff = round(this_pct - prev_pct, 1)
            arrow = '↑' if diff > 0 else '↓' if diff < 0 else '→'
            on_time_trend = f"{arrow} {abs(diff)}% vs last week"
            on_time_trend_class = 'trend-up' if diff > 0 else 'trend-down' if diff < 0 else 'trend-flat'

            # Delay trend similarly
            def delay_pct(series):
                total = len(series)
                if total == 0:
                    return 0.0
                delayed = series.str.lower().str.contains('delay|late')
                return round((delayed.sum() / total) * 100, 1)

            prev_delay = delay_pct(prev_week.get('status').fillna('')) if not prev_week.empty else 0.0
            this_delay = delay_pct(this_week.get('status').fillna('')) if not this_week.empty else delay_pct(df['status_resolved'])
            d_diff = round(this_delay - prev_delay, 1)
            d_arrow = '↑' if d_diff > 0 else '↓' if d_diff < 0 else '→'
            delay_trend = f"{d_arrow} {abs(d_diff)}% vs last week"
            delay_trend_class = 'trend-up' if d_diff > 0 else 'trend-down' if d_diff < 0 else 'trend-flat'
        except Exception as _:
            pass

        report = {
            'total_flights': int(total_flights),
            'arrivals': int(arrivals),
            'departures': int(departures),
            'avg_daily_flights': float(avg_daily),
            'on_time_percentage': float(on_time_pct),
            'delay_percentage': float(delay_pct),
            'total_delays': int(delayed),
            'total_cancelled': int(cancelled),
            'busiest_day': str(busiest_day),
            'busiest_day_count': int(busiest_day_count),
            'top_route': str(top_route),
            'top_route_count': int(top_route_count),
            'peak_hour': str(peak_hour),
            'on_time_trend': str(on_time_trend),
            'on_time_trend_class': str(on_time_trend_class),
            'delay_trend': str(delay_trend),
            'delay_trend_class': str(delay_trend_class),
            'generated_at': datetime.now().isoformat()
        }

        logger.info(f"✓ Weekly report generated from HDF5: {total_flights} flights, avg {avg_daily}/day")
        return jsonify(report)

    except Exception as e:
        logger.error(f"✗ Error generating weekly report: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/plot/<name>')
def api_plot(name):
    """Plot endpoint - temporarily disabled for performance (plots were using slow legacy tracker)"""
    # Return a simple message instead of generating plots
    # The dashboard uses Chart.js for real-time visualization instead
    return jsonify({
        'message': 'Plot generation disabled for performance - use real-time dashboard charts',
        'plot_name': name
    }), 200


@app.route('/api/send-email', methods=['POST'])
def send_email():
    """
    Send email reports via Gmail SMTP
    
    Request body:
    {
        "to": "recipient@gmail.com",
        "subject": "Email Subject",
        "html": "<html>Email body</html>",
        "report_type": "daily|weekly"
    }
    
    Returns:
        JSON response with success/error status
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        data = request.json
        recipient = data.get('to', 'bigjaminben@gmail.com')
        subject = data.get('subject', 'ICT Airport Report')
        html_body = data.get('html', '')
        report_type = data.get('report_type', 'daily')
        
        # Gmail SMTP Configuration
        SENDER_EMAIL = "bigjaminben@gmail.com"
        APP_PASSWORD = "jehz xfee xmip nezy"
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient
        
        # Attach HTML content
        msg.attach(MIMEText(html_body, "html"))
        
        # Send email via Gmail
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
        
        logger.info(f"✓ {report_type.upper()} email sent to {recipient}")
        return jsonify({
            'success': True,
            'message': f'{report_type.capitalize()} report sent successfully',
            'recipient': recipient,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(f"✗ {error_msg}")
        return jsonify({
            'success': False,
            'message': error_msg,
            'error': str(e)
        }), 500


# ============================================================================
# ADVANCED REPORT ENDPOINTS FOR NODE-RED
# ============================================================================

@app.route('/api/report/executive-summary')
def api_executive_summary():
    """
    Executive summary report with KPIs and trends for management
    Includes performance metrics, critical alerts, and actionable insights
    """
    try:
        logger.info("Generating executive summary report...")
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()
        
        arrivals = [f for f in flights if f.get('Type') == 'Arrival']
        departures = [f for f in flights if f.get('Type') == 'Departure']
        
        on_time = sum(1 for f in flights if 'land' in (f.get('Status') or '').lower() 
                     or 'arrived' in (f.get('Status') or '').lower()
                     or 'departing' in (f.get('Status') or '').lower())
        delayed = sum(1 for f in flights if 'delay' in (f.get('Status') or '').lower())
        cancelled = sum(1 for f in flights if 'cancel' in (f.get('Status') or '').lower())
        
        total = len(flights) if len(flights) > 0 else 1
        on_time_pct = round((on_time / total) * 100, 1)
        delay_pct = round((delayed / total) * 100, 1)
        
        # Calculate average delay
        avg_delay = 0
        delay_minutes = []
        for flight in flights:
            if 'delay' in (flight.get('Status') or '').lower():
                try:
                    # Extract delay minutes if available
                    delay_minutes.append(15)  # Default estimate
                except:
                    pass
        
        avg_delay = round(sum(delay_minutes) / len(delay_minutes)) if delay_minutes else 0
        
        report = {
            'report_type': 'executive_summary',
            'period': 'daily',
            'generated_at': datetime.now().isoformat(),
            'kpis': {
                'total_flights': len(flights),
                'arrivals': len(arrivals),
                'departures': len(departures),
                'on_time_percentage': on_time_pct,
                'on_time_flights': on_time,
                'delay_percentage': delay_pct,
                'delayed_flights': delayed,
                'cancelled_flights': cancelled,
                'average_delay_minutes': avg_delay
            },
            'operational_status': 'normal' if on_time_pct >= 85 else 'degraded' if on_time_pct >= 70 else 'critical',
            'alerts': [
                {'level': 'warning', 'message': f'{delayed} flights delayed'} if delayed > 5 else None,
                {'level': 'info', 'message': f'Peak hour analysis available'} if len(flights) > 0 else None
            ],
            'alerts': [a for a in [
                {'level': 'warning', 'message': f'{delayed} flights delayed'} if delayed > 5 else None,
                {'level': 'info', 'message': 'Normal operations'} if on_time_pct >= 85 else None
            ] if a is not None]
        }
        
        logger.info(f"✓ Executive summary generated - {on_time_pct}% on-time performance")
        return jsonify(report), 200
        
    except Exception as e:
        logger.error(f"✗ Error generating executive summary: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/delays')
def api_delay_report():
    """
    Detailed delay analysis report with delay causes and affected routes
    """
    try:
        logger.info("Generating delay analysis report...")
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()
        
        delayed_flights = [f for f in flights if 'delay' in (f.get('Status') or '').lower()]
        
        # Group delays by route
        delay_by_route = {}
        for flight in delayed_flights:
            if flight.get('Type') == 'Arrival':
                route = f"{flight.get('Origin', 'N/A')} → ICT"
            else:
                route = f"ICT → {flight.get('Destination', 'N/A')}"
            
            if route not in delay_by_route:
                delay_by_route[route] = {'count': 0, 'flights': []}
            
            delay_by_route[route]['count'] += 1
            delay_by_route[route]['flights'].append({
                'flight_number': flight.get('Flight_Number', 'N/A'),
                'airline': flight.get('Airline', 'N/A'),
                'status': flight.get('Status', 'N/A'),
                'scheduled_time': flight.get('Scheduled_Time', 'N/A')
            })
        
        report = {
            'report_type': 'delay_analysis',
            'total_delayed_flights': len(delayed_flights),
            'delays_by_route': delay_by_route,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"✓ Delay report generated - {len(delayed_flights)} delayed flights")
        return jsonify(report), 200
        
    except Exception as e:
        logger.error(f"✗ Error generating delay report: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/performance-metrics')
def api_performance_metrics():
    """
    Comprehensive performance metrics including KPIs, trends, and benchmarks
    """
    try:
        logger.info("Generating performance metrics...")
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()
        
        if len(flights) == 0:
            return jsonify({
                'report_type': 'performance_metrics',
                'message': 'No flight data available',
                'generated_at': datetime.now().isoformat()
            }), 200
        
        # Calculate metrics
        arrivals = len([f for f in flights if f.get('Type') == 'Arrival'])
        departures = len([f for f in flights if f.get('Type') == 'Departure'])
        on_time = sum(1 for f in flights if 'land' in (f.get('Status') or '').lower() 
                     or 'arrived' in (f.get('Status') or '').lower()
                     or 'departing' in (f.get('Status') or '').lower())
        delayed = sum(1 for f in flights if 'delay' in (f.get('Status') or '').lower())
        cancelled = sum(1 for f in flights if 'cancel' in (f.get('Status') or '').lower())
        
        total = len(flights)
        on_time_pct = round((on_time / total) * 100, 1)
        delay_pct = round((delayed / total) * 100, 1)
        cancellation_pct = round((cancelled / total) * 100, 1)
        
        # Airline performance
        airline_counts = {}
        for flight in flights:
            airline = flight.get('Airline', 'Unknown')
            if airline not in airline_counts:
                airline_counts[airline] = {'count': 0, 'on_time': 0, 'delayed': 0}
            
            airline_counts[airline]['count'] += 1
            status = (flight.get('Status') or '').lower()
            if 'land' in status or 'arrived' in status or 'departing' in status:
                airline_counts[airline]['on_time'] += 1
            elif 'delay' in status:
                airline_counts[airline]['delayed'] += 1
        
        # Calculate airline on-time percentages
        airline_metrics = {}
        for airline, data in airline_counts.items():
            if data['count'] > 0:
                airline_metrics[airline] = {
                    'flights': data['count'],
                    'on_time_percentage': round((data['on_time'] / data['count']) * 100, 1)
                }
        
        report = {
            'report_type': 'performance_metrics',
            'summary': {
                'total_flights': total,
                'arrivals': arrivals,
                'departures': departures
            },
            'performance': {
                'on_time_percentage': on_time_pct,
                'on_time_flights': on_time,
                'delay_percentage': delay_pct,
                'delayed_flights': delayed,
                'cancellation_percentage': cancellation_pct,
                'cancelled_flights': cancelled
            },
            'airline_performance': airline_metrics,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"✓ Performance metrics generated - {on_time_pct}% on-time")
        return jsonify(report), 200
        
    except Exception as e:
        logger.error(f"✗ Error generating performance metrics: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/route-analysis')
def api_route_analysis():
    """
    Detailed route analysis including flight counts and performance by route
    """
    try:
        logger.info("Generating route analysis report...")
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()
        
        # Analyze by route
        routes = {}
        for flight in flights:
            if flight.get('Type') == 'Arrival':
                route = f"{flight.get('Origin', 'N/A')} → ICT"
            else:
                route = f"ICT → {flight.get('Destination', 'N/A')}"
            
            if route not in routes:
                routes[route] = {'count': 0, 'on_time': 0, 'delayed': 0, 'cancelled': 0}
            
            routes[route]['count'] += 1
            status = (flight.get('Status') or '').lower()
            if 'land' in status or 'arrived' in status or 'departing' in status:
                routes[route]['on_time'] += 1
            elif 'delay' in status:
                routes[route]['delayed'] += 1
            elif 'cancel' in status:
                routes[route]['cancelled'] += 1
        
        # Calculate route metrics
        route_metrics = {}
        for route, data in routes.items():
            if data['count'] > 0:
                route_metrics[route] = {
                    'flights': data['count'],
                    'on_time_percentage': round((data['on_time'] / data['count']) * 100, 1),
                    'delayed': data['delayed'],
                    'cancelled': data['cancelled']
                }
        
        # Sort by flight count descending
        sorted_routes = dict(sorted(route_metrics.items(), key=lambda x: x[1]['flights'], reverse=True))
        
        report = {
            'report_type': 'route_analysis',
            'total_unique_routes': len(sorted_routes),
            'routes': sorted_routes,
            'busiest_route': next(iter(sorted_routes)) if sorted_routes else 'N/A',
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"✓ Route analysis generated - {len(sorted_routes)} unique routes")
        return jsonify(report), 200
        
    except Exception as e:
        logger.error(f"✗ Error generating route analysis: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/node-red/health')
def node_red_health():
    """
    Health check endpoint for Node Red to verify API connectivity
    """
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'ICT Airport API Server',
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat(),
            'endpoints': {
                'daily_report': '/api/report/daily',
                'weekly_report': '/api/report/weekly',
                'executive_summary': '/api/report/executive-summary',
                'delays': '/api/report/delays',
                'performance': '/api/report/performance-metrics',
                'routes': '/api/report/route-analysis'
            }
        }), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/api/node-red/report/batch', methods=['GET'])
def node_red_batch_report():
    """
    Generate all reports in one call for Node Red efficiency
    Returns all report types needed for email generation
    """
    try:
        logger.info("Generating batch report for Node Red...")
        aggregator = get_lazy_aggregator()
        flights = aggregator.get_all_flights()
        
        arrivals = [f for f in flights if f.get('Type') == 'Arrival']
        departures = [f for f in flights if f.get('Type') == 'Departure']
        
        on_time = sum(1 for f in flights if 'land' in (f.get('Status') or '').lower() 
                     or 'arrived' in (f.get('Status') or '').lower()
                     or 'departing' in (f.get('Status') or '').lower())
        delayed = sum(1 for f in flights if 'delay' in (f.get('Status') or '').lower())
        cancelled = sum(1 for f in flights if 'cancel' in (f.get('Status') or '').lower())
        
        total = len(flights) if len(flights) > 0 else 1
        on_time_pct = round((on_time / total) * 100, 1)
        delay_pct = round((delayed / total) * 100, 1)
        
        # Busiest hour
        hour_counts = {}
        for flight in flights:
            sched_time = flight.get('Scheduled_Time', '')
            if sched_time:
                try:
                    if 'T' in sched_time:
                        hour = int(sched_time.split('T')[1].split(':')[0])
                    else:
                        hour = int(sched_time.split(':')[0])
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except:
                    pass
        
        busiest_hour = 'N/A'
        if hour_counts:
            max_hour = max(hour_counts.items(), key=lambda x: x[1])
            hour_12 = max_hour[0] if max_hour[0] <= 12 else max_hour[0] - 12
            hour_12 = 12 if hour_12 == 0 else hour_12
            ampm = 'AM' if max_hour[0] < 12 else 'PM'
            busiest_hour = f"{hour_12}:00 {ampm} ({max_hour[1]} flights)"
        
        # Top route
        route_counts = {}
        for flight in flights:
            if flight.get('Type') == 'Arrival':
                route = f"{flight.get('Origin', 'N/A')} → ICT"
            else:
                route = f"ICT → {flight.get('Destination', 'N/A')}"
            route_counts[route] = route_counts.get(route, 0) + 1
        
        top_route = 'N/A'
        if route_counts:
            max_route = max(route_counts.items(), key=lambda x: x[1])
            top_route = f"{max_route[0]} ({max_route[1]} flights)"
        
        batch_report = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'total_flights': len(flights),
                'arrivals': len(arrivals),
                'departures': len(departures),
                'on_time': on_time,
                'on_time_percentage': on_time_pct,
                'delayed': delayed,
                'delay_percentage': delay_pct,
                'cancelled': cancelled,
                'busiest_hour': busiest_hour,
                'top_route': top_route
            }
        }
        
        logger.info(f"✓ Batch report generated successfully")
        return jsonify(batch_report), 200
        
    except Exception as e:
        logger.error(f"✗ Error generating batch report: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/health')
def api_health():
    """
    Consolidated health check for UI and monitoring.
    Reports overall system status and component details.
    """
    try:
        started = time.time()

        api_status = {
            'name': 'api',
            'ok': True,
            'version': '2.0.0',
            'latency_ms': 0
        }

        # Redis
        redis_ok = _redis_cache.is_available()
        redis_stats = _redis_cache.get_stats() if redis_ok else {'enabled': False}
        redis_status = {
            'name': 'redis',
            'ok': bool(redis_ok),
            'details': redis_stats
        }

        # Node-RED
        try:
            nr = NodeRedManager.check_health()
            node_red_ok = nr.get('running', False) and nr.get('status') == 'healthy'
        except Exception:
            nr = {'status': 'unhealthy', 'running': False}
            node_red_ok = False
        node_red_status = {
            'name': 'node_red',
            'ok': bool(node_red_ok),
            'details': nr
        }

        # HDF5
        try:
            stats = get_storage().get_statistics()
            h5_ok = True
            h5_details = stats
        except Exception as e:
            h5_ok = False
            h5_details = {'error': str(e)}
        hdf5_status = {
            'name': 'hdf5',
            'ok': bool(h5_ok),
            'details': h5_details
        }

        # Flights cache presence
        cached = _redis_cache.get('flights_all_response')
        flights_cache_ok = cached is not None
        flights_cache_status = {
            'name': 'flights_cache',
            'ok': bool(flights_cache_ok)
        }

        # Compose
        components = [api_status, redis_status, node_red_status, hdf5_status, flights_cache_status]
        overall_ok = all(c.get('ok') for c in components)
        degraded = not overall_ok and any(c.get('ok') for c in components)
        latency_ms = int((time.time() - started) * 1000)
        api_status['latency_ms'] = latency_ms

        status = 'healthy' if overall_ok else 'degraded' if degraded else 'unhealthy'

        return jsonify({
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'latency_ms': latency_ms,
            'components': {
                'api': api_status,
                'redis': redis_status,
                'node_red': node_red_status,
                'hdf5': hdf5_status,
                'flights_cache': flights_cache_status
            }
        }), 200
    except Exception as e:
        logger.error(f"Health endpoint error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


# The Flask `app` instance is defined above. Can run directly or via serve_prod.py

if __name__ == '__main__':
    print("Starting Flight Tracker API with real data...")
    print("Server will be available at http://127.0.0.1:5001")
    app.run(host='127.0.0.1', port=5001, debug=False, threaded=True)
