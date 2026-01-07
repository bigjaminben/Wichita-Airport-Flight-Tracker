"""
Enterprise Logging Infrastructure
Structured logging with correlation IDs and distributed tracing support
"""
import logging
import sys
import uuid
from typing import Optional
from datetime import datetime
from pythonjsonlogger import jsonlogger
from flask import g, request, has_request_context
from config import get_settings

settings = get_settings()


class RequestIdFilter(logging.Filter):
    """Add correlation ID to all log records"""
    
    def filter(self, record):
        if has_request_context():
            record.correlation_id = getattr(g, 'correlation_id', 'no-request')
            record.method = request.method
            record.path = request.path
            record.remote_addr = request.remote_addr
        else:
            record.correlation_id = 'system'
            record.method = '-'
            record.path = '-'
            record.remote_addr = '-'
        
        record.service = settings.APP_NAME
        record.version = settings.APP_VERSION
        record.environment = settings.ENVIRONMENT
        
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with enterprise fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add thread info for debugging
        log_record['thread_id'] = record.thread
        log_record['process_id'] = record.process
        
        # Add location info for debugging
        if settings.DEBUG:
            log_record['file'] = record.pathname
            log_record['line'] = record.lineno
            log_record['function'] = record.funcName


def setup_logging():
    """Configure enterprise-grade logging"""
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level
    log_level = getattr(logging, settings.LOG_LEVEL)
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Add request ID filter
    request_filter = RequestIdFilter()
    console_handler.addFilter(request_filter)
    
    # Format based on configuration
    if settings.LOG_FORMAT == 'json':
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(correlation_id)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.LOG_FILE:
        import os
        os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
        
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(log_level)
        file_handler.addFilter(request_filter)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


def add_correlation_id():
    """Middleware to add correlation ID to request context"""
    if not has_request_context():
        return
    
    # Get or generate correlation ID
    correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
    g.correlation_id = correlation_id


def log_request_info(logger: logging.Logger):
    """Log request information"""
    if not has_request_context():
        return
    
    logger.info(
        "Request received",
        extra={
            'method': request.method,
            'path': request.path,
            'user_agent': request.user_agent.string,
            'content_length': request.content_length,
            'query_params': dict(request.args)
        }
    )


def log_response_info(logger: logging.Logger, response, duration_ms: float):
    """Log response information"""
    if not has_request_context():
        return
    
    logger.info(
        "Response sent",
        extra={
            'status_code': response.status_code,
            'content_length': response.content_length,
            'duration_ms': duration_ms
        }
    )
