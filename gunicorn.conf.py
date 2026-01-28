# Gunicorn configuration file for production deployment

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/progressreport/access.log"
errorlog = "/var/log/progressreport/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process name
proc_name = "progressreport"

# Security
user = "www-data"
group = "www-data"

# Auto restart
max_requests = 1000
max_requests_jitter = 50
preload_app = True 