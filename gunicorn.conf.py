# Linux production (many CPU cores):  gunicorn -c gunicorn.conf.py app:app
import multiprocessing, os
bind = '0.0.0.0:%s' % os.environ.get('PORT', 5000)
workers = int(os.environ.get('WORKERS', multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get('THREADS', 4))
worker_class = 'gthread'
timeout = 60
graceful_timeout = 30
keepalive = 5
max_requests = 5000            # restart a worker now and then: keeps memory flat for months
max_requests_jitter = 500
accesslog = None
errorlog = '-'
