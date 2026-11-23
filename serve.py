"""Production server (Waitress - works on Windows and Linux).   Start:  python serve.py
Settings come from environment variables:  HOST, PORT, THREADS, DATABASE_URL, SECRET_KEY, HTTPS, BEHIND_PROXY ..."""
import os, threading, time, logging
from waitress import serve
from app import app, IS_SQLITE

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5000))
THREADS = int(os.environ.get('THREADS', 24))


def daily_backup():
    """Automatic backup once a day (SQLite mode)."""
    from backup import backup_sqlite
    last = None
    while True:
        today = time.strftime('%Y%m%d')
        if today != last:
            try:
                backup_sqlite()
                last = today
            except Exception:
                app.logger.exception('automatic backup failed')
        time.sleep(1800)


if __name__ == '__main__':
    if IS_SQLITE and os.environ.get('AUTO_BACKUP', '1') == '1':
        threading.Thread(target=daily_backup, daemon=True).start()
    logging.getLogger('waitress').setLevel(logging.WARNING)
    print('Lion Enviro Attendance running on http://%s:%s  (threads=%s)  - press Ctrl+C to stop' % (HOST, PORT, THREADS))
    serve(app, host=HOST, port=PORT, threads=THREADS, connection_limit=2000, backlog=2048,
          channel_timeout=60, cleanup_interval=10, max_request_body_size=2 * 1024 * 1024,
          ident='attendance', url_scheme='https' if os.environ.get('HTTPS') == '1' else 'http')
