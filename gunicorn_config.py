"""
Enterprise Production Server Startup
Gunicorn configuration for production deployment
"""

import multiprocessing
import os
from config import get_settings

settings = get_settings()

# Server socket
bind = f"{settings.HOST}:{settings.PORT}"
backlog = 2048

# Worker processes
workers = settings.WORKERS
worker_class = settings.WORKER_CLASS
worker_connections = 1000
timeout = settings.WORKER_TIMEOUT
keepalive = 5

# Threading
threads = 4 if settings.WORKER_CLASS == 'gthread' else 1

# Process naming
proc_name = 'flight_tracker_enterprise'

# Logging
accesslog = 'logs/access.log'
errorlog = 'logs/error.log'
loglevel = settings.LOG_LEVEL.lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
daemon = False
pidfile = 'gunicorn.pid'
umask = 0
tmp_upload_dir = None

# SSL (if certificates are available)
# keyfile = '/path/to/key.pem'
# certfile = '/path/to/cert.pem'

# Hooks
def on_starting(server):
    """Called just before the master process is initialized"""
    print(f"Starting Gunicorn server with {workers} workers")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    print("Reloading workers...")

def when_ready(server):
    """Called just after the server is started"""
    print(f"Server is ready. Listening on {bind}")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    print(f"Worker spawned (pid: {worker.pid})")

def post_worker_init(worker):
    """Called just after a worker has initialized the application"""
    print(f"Worker initialized (pid: {worker.pid})")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT"""
    print(f"Worker interrupted (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal"""
    print(f"Worker aborted (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked"""
    print("Forking new master process...")

def pre_request(worker, req):
    """Called just before a worker processes the request"""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request"""
    pass

def child_exit(server, worker):
    """Called just after a worker has been exited"""
    print(f"Worker exited (pid: {worker.pid})")

def worker_exit(server, worker):
    """Called just after a worker has been exited"""
    pass

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed"""
    print(f"Workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Called just before exiting Gunicorn"""
    print("Shutting down Gunicorn server")
