# Gunicorn configuration file for production deployment

# 서버 소켓
bind = "0.0.0.0:8000"
backlog = 2048

# 워커 프로세스
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 로깅
accesslog = "/var/log/progressreport/access.log"
errorlog = "/var/log/progressreport/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 프로세스 이름
proc_name = "progressreport"

# 보안
user = "www-data"
group = "www-data"

# 자동 재시작
max_requests = 1000
max_requests_jitter = 50
preload_app = True 