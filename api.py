from flask import Flask, jsonify, send_file, make_response, send_from_directory, request
import io
import os
import importlib.util
import logging
import matplotlib
# Use non-GUI backend for server-side rendering to avoid GUI backend errors
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import time
import threading
import gzip

# Import enhanced data sources
from data_sources import get_aggregator, AirportStatistics

# Import Redis cache manager
from redis_cache import get_cache

# Import delay predictor
from delay_predictor import get_predictor

# Initialize Redis cache
_redis_cache = get_cache()

APP_FILE = os.path.join(os.path.dirname(__file__), 'Airport Tracker.py')


def load_tracker():
    """Dynamically load the AirportFlightTrackerWithGraphs class from the script file.
    This avoids renaming the original script which has a space in the filename.
    """
    spec = importlib.util.spec_from_file_location('airport_module', APP_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TrackerClass = getattr(module, 'AirportFlightTrackerWithGraphs')
    # Instantiate; the constructor fetches live data automatically
    tracker = TrackerClass(None, None)
    return tracker


def to_serializable(obj):
    """Helper to convert non-JSON types to serializable forms."""
    try:
        import numpy as _np
        if isinstance(obj, _np.generic):
            # use .item() which works for numpy scalars and avoids deprecated asscalar
            return obj.item()
    except Exception:
        pass
    return str(obj)


app = Flask(__name__)
app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'text/xml', 'application/json', 'application/javascript']
app.config['COMPRESS_LEVEL'] = 6
app.config['COMPRESS_MIN_SIZE'] = 500
tracker = None
_tracker_initialized = False
# Caching configuration (seconds) - increased for better performance
CACHE_TTL = 30  # Increased from 20 to reduce API load

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


def _setup_tracker():
    """Initialize tracker and cache on first request."""
    global tracker, _tracker_initialized
    if _tracker_initialized:
        return
    tracker = load_tracker()
    # initialize cache immediately
    try:
        tracker.create_sample_data_if_missing()
    except Exception:
        pass
    with _cache_lock:
        _cache['data_ts'] = time.time()
        _cache['flights_json'] = json.dumps(tracker.flights_data or [], default=to_serializable)
        _cache['weather_json'] = json.dumps(tracker.weather_data or {}, default=to_serializable)
    _tracker_initialized = True


@app.before_request
def _ensure_tracker_ready():
    """Ensure tracker is initialized before handling any request."""
    _setup_tracker()


def ensure_fresh_data():
    """Ensure tracker data and cache are fresh within CACHE_TTL seconds using Redis."""
    global tracker
    now = time.time()
    
    # Check Redis cache first
    if _redis_cache.is_available():
        cached_flights = _redis_cache.get('flights_json')
        if cached_flights:
            with _cache_lock:
                _cache['flights_json'] = cached_flights
                _cache['data_ts'] = now
            return
    
    # Fall back to memory cache check
    with _cache_lock:
        if now - _cache['data_ts'] < CACHE_TTL and _cache['flights_json'] is not None:
            return
    
    # Refresh data
    if tracker is None:
        tracker = load_tracker()
    try:
        tracker.create_sample_data_if_missing()
    except Exception:
        pass
    
    with _cache_lock:
        _cache['data_ts'] = time.time()
        _cache['flights_json'] = json.dumps(tracker.flights_data or [], default=to_serializable)
        _cache['weather_json'] = json.dumps(tracker.weather_data or {}, default=to_serializable)
        
        # Cache in Redis with TTL
        _redis_cache.set('flights_json', _cache['flights_json'], CACHE_TTL)
        _redis_cache.set('weather_json', _cache['weather_json'], CACHE_TTL)
        _redis_cache.set('data_ts', str(_cache['data_ts']), CACHE_TTL)


@app.route('/api/flights')
def api_flights():
    ensure_fresh_data()
    with _cache_lock:
        flights_data = json.loads(_cache['flights_json']) if _cache['flights_json'] else []
        return jsonify(flights_data)


@app.route('/api/flights/all')
def api_flights_all():
    """Get flights from all sources (Flightradar24, Airportia, OpenSky)"""
    try:
        # Check cache first
        cached = _redis_cache.get('flights_all_response')
        if cached:
            return jsonify_compressed(json.loads(cached))
        
        aggregator = get_aggregator()
        all_flights = aggregator.get_all_flights()
        
        response_data = {
            'flights': all_flights,
            'count': len(all_flights),
            'sources': ['Flightradar24', 'Airportia', 'OpenSky'],
            'timestamp': time.time()
        }
        
        # Cache the response
        _redis_cache.set('flights_all_response', json.dumps(response_data), CACHE_TTL)
        
        return jsonify_compressed(response_data)
    except Exception as e:
        return jsonify({'error': str(e), 'flights': []}), 500


@app.route('/api/flights/flightradar24')
def api_flights_fr24():
    """Get flights from Flightradar24 only"""
    try:
        aggregator = get_aggregator()
        flights = aggregator.fetch_flightradar24_data()
        return jsonify({
            'flights': flights,
            'count': len(flights),
            'source': 'Flightradar24',
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e), 'flights': []}), 500


@app.route('/api/flights/airportia')
def api_flights_airportia():
    """Get arrivals and departures from Airportia"""
    try:
        aggregator = get_aggregator()
        data = aggregator.fetch_airportia_data()
        return jsonify({
            'arrivals': data.get('arrivals', []),
            'departures': data.get('departures', []),
            'arrivals_count': len(data.get('arrivals', [])),
            'departures_count': len(data.get('departures', [])),
            'source': 'Airportia',
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/flights/history')
def api_flights_history():
    """Get today's flight history from database"""
    try:
        aggregator = get_aggregator()
        history = aggregator.get_todays_history()
        stats = aggregator.get_history_stats()
        return jsonify({
            'arrivals': history.get('arrivals', []),
            'departures': history.get('departures', []),
            'stats': stats,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    ensure_fresh_data()
    with _cache_lock:
        weather_data = json.loads(_cache['weather_json']) if _cache['weather_json'] else {}
        return jsonify(weather_data)


def render_plot_from_method(method_name):
    """Call a plotting method on the tracker and return the PNG bytes.
    We monkeypatch plt.show to a no-op while calling the method so it doesn't block.
    """
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
    """Get today's operations log"""
    try:
        from operations_logger import operations_log
        ops = operations_log.get_today_operations()
        summary = operations_log.get_daily_summary()
        return jsonify({
            'operations': ops,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        aggregator = get_aggregator()
        all_flights = aggregator.get_all_flights()
        
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


@app.route('/api/plot/<name>')
def api_plot(name):
    if name not in PLOT_METHODS:
        return jsonify({'error': f'Unknown plot {name}'}), 404
    ensure_fresh_data()
    now = time.time()
    with _cache_lock:
        cached = _cache['plots'].get(name)
        if cached and (now - cached[0] < CACHE_TTL):
            # return cached bytes
            return send_file(io.BytesIO(cached[1]), mimetype='image/png', download_name=f'{name}.png')
    # generate plot bytes and cache
    data_bytes, err = render_plot_from_method(PLOT_METHODS[name])
    if err:
        return jsonify({'error': err}), 500
    with _cache_lock:
        _cache['plots'][name] = (time.time(), data_bytes)
    return send_file(io.BytesIO(data_bytes), mimetype='image/png', download_name=f'{name}.png')


# The Flask `app` instance is defined above. Do not start the development server
# here; use `serve_prod.py` (Waitress) or `run_server.ps1` to run the application
# in production. This file is intentionally not executable as a script to avoid
# accidental starts with the Flask development server.
