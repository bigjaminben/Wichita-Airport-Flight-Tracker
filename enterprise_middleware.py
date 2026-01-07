"""
Enterprise Middleware
Authentication, monitoring, error handling, and security headers
"""
import time
import functools
from flask import request, jsonify, g
from werkzeug.exceptions import HTTPException
from prometheus_client import Counter, Histogram, Gauge
from config import get_settings
from enterprise_logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Number of active HTTP requests'
)

ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['endpoint', 'error_type']
)

CACHE_HIT_COUNT = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['endpoint']
)

CACHE_MISS_COUNT = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['endpoint']
)


def require_api_key(f):
    """Decorator to require API key authentication"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth for health checks
        if request.path in ['/health', '/metrics', '/ready']:
            return f(*args, **kwargs)
        
        api_key = request.headers.get(settings.API_KEY_HEADER)
        
        if not api_key:
            logger.warning(
                "Missing API key",
                extra={'path': request.path, 'ip': request.remote_addr}
            )
            return jsonify({
                'error': 'Missing API key',
                'message': f'Please provide API key in {settings.API_KEY_HEADER} header'
            }), 401
        
        if api_key not in settings.ALLOWED_API_KEYS:
            logger.warning(
                "Invalid API key",
                extra={'path': request.path, 'ip': request.remote_addr, 'key': api_key[:10]}
            )
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 403
        
        g.api_key = api_key
        return f(*args, **kwargs)
    
    return decorated_function


def add_security_headers(response):
    """Add enterprise security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # Add correlation ID to response
    if hasattr(g, 'correlation_id'):
        response.headers['X-Correlation-ID'] = g.correlation_id
    
    return response


def track_metrics(response):
    """Track request metrics"""
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown'
        ).observe(duration)
    
    return response


def handle_errors(app):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.error("Bad request", extra={'error': str(error)})
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='400').inc()
        return jsonify({
            'error': 'Bad Request',
            'message': str(error),
            'correlation_id': getattr(g, 'correlation_id', None)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        logger.error("Unauthorized", extra={'error': str(error)})
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='401').inc()
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'correlation_id': getattr(g, 'correlation_id', None)
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        logger.error("Forbidden", extra={'error': str(error)})
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='403').inc()
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied',
            'correlation_id': getattr(g, 'correlation_id', None)
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning("Not found", extra={'path': request.path})
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='404').inc()
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'correlation_id': getattr(g, 'correlation_id', None)
        }), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        logger.warning("Rate limit exceeded", extra={'ip': request.remote_addr})
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='429').inc()
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.',
            'correlation_id': getattr(g, 'correlation_id', None)
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error("Internal server error", exc_info=True)
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='500').inc()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred' if not settings.DEBUG else str(error),
            'correlation_id': getattr(g, 'correlation_id', None)
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        logger.error("Service unavailable", extra={'error': str(error)})
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='503').inc()
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'The service is temporarily unavailable',
            'correlation_id': getattr(g, 'correlation_id', None)
        }), 503
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.error("Unexpected error", exc_info=True)
        ERROR_COUNT.labels(endpoint=request.endpoint or 'unknown', error_type='unexpected').inc()
        
        # Return generic error in production
        if not settings.DEBUG:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'correlation_id': getattr(g, 'correlation_id', None)
            }), 500
        else:
            # Include details in development
            return jsonify({
                'error': 'Internal Server Error',
                'message': str(error),
                'type': type(error).__name__,
                'correlation_id': getattr(g, 'correlation_id', None)
            }), 500


def before_request_middleware():
    """Execute before each request"""
    g.start_time = time.time()
    ACTIVE_REQUESTS.inc()


def after_request_middleware(response):
    """Execute after each request"""
    ACTIVE_REQUESTS.dec()
    return response


def record_cache_hit():
    """Record cache hit metric"""
    CACHE_HIT_COUNT.labels(endpoint=request.endpoint or 'unknown').inc()


def record_cache_miss():
    """Record cache miss metric"""
    CACHE_MISS_COUNT.labels(endpoint=request.endpoint or 'unknown').inc()
