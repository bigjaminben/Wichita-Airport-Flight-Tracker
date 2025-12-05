from flask import Flask, jsonify, send_file, make_response, send_from_directory
import io
import os
import importlib.util
import matplotlib
# Use non-GUI backend for server-side rendering to avoid GUI backend errors
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import time
import threading

# Import enhanced data sources
from data_sources import get_aggregator, AirportStatistics

# Optional Redis caching (if REDIS_URL is set in env). Falls back to in-memory cache.
REDIS_URL = os.environ.get('REDIS_URL')
_redis_client = None
if REDIS_URL:
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    except Exception:
        _redis_client = None

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
tracker = None
_tracker_initialized = False
# Caching configuration (seconds)
CACHE_TTL = 15

# In-memory cache structure
_cache = {
    'data_ts': 0.0,
    'flights_json': None,
    'weather_json': None,
    'plots': {}  # name -> (ts, bytes)
}
_cache_lock = threading.Lock()


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
    """Ensure tracker data and JSON cache are fresh within CACHE_TTL seconds."""
    global tracker
    now = time.time()
    with _cache_lock:
        if now - _cache['data_ts'] < CACHE_TTL and _cache['flights_json'] is not None:
            return
    # refresh data
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
        # if redis is available, also prime redis cache
        if _redis_client:
            try:
                _redis_client.set('flights_json', _cache['flights_json'], ex=CACHE_TTL)
                _redis_client.set('weather_json', _cache['weather_json'], ex=CACHE_TTL)
                _redis_client.set('data_ts', str(_cache['data_ts']), ex=CACHE_TTL)
            except Exception:
                pass


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
        aggregator = get_aggregator()
        all_flights = aggregator.get_all_flights()
        return jsonify({
            'flights': all_flights,
            'count': len(all_flights),
            'sources': ['Flightradar24', 'Airportia', 'OpenSky'],
            'timestamp': time.time()
        })
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
