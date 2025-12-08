"""WSGI launcher for production: runs the Flask `app` using waitress.

This file configures a RotatingFileHandler and redirects stdout/stderr into
the logger so logs rotate cleanly and are captured regardless of process redirection.

Usage: python serve_prod.py --host 127.0.0.1 --port 5001
"""
import argparse
import logging
import logging.handlers
import os
import sys


class StreamToLogger(object):
    """Fake file-like stream object that redirects writes to a logger instance."""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass


def configure_logging(root_dir):
    logs_dir = root_dir
    log_path = os.path.join(logs_dir, 'server.log')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Rotating file handler: 5 MB per file, keep 5 backups
    handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Also log to console (optional)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Redirect stdout/stderr to logging
    sys.stdout = StreamToLogger(logger, logging.INFO)
    sys.stderr = StreamToLogger(logger, logging.ERROR)

    return logger


def main():
    parser = argparse.ArgumentParser(description='Run Airport Tracker with Waitress')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()

    root_dir = os.path.dirname(__file__)
    logger = configure_logging(root_dir)

    logger.info('Starting production server using Waitress')

    # Import the Flask app from api.py
    from api import app

    try:
        from waitress import serve
    except Exception:
        logger.exception('Waitress is not installed. Please run: pip install waitress')
        raise

    # Ensure waitress logs propagate to our logging configuration
    logging.getLogger('waitress').setLevel(logging.INFO)

    logger.info(f'Serving on http://{args.host}:{args.port}')
    # Optimize Waitress settings for better performance
    serve(app, host=args.host, port=args.port, threads=6, channel_timeout=120, cleanup_interval=10)


if __name__ == '__main__':
    main()
