"""Safe database backup.  SQLite: consistent online copy (works while the app is running).
MySQL: use mysqldump (see README).  Usage:  python backup.py"""
import os, sqlite3, glob, time
from app import DATA_DIR, DB_URL, IS_SQLITE

KEEP = int(os.environ.get('BACKUP_KEEP', 14))          # how many daily copies to keep


def backup_sqlite():
    if not IS_SQLITE:
        print('MySQL/PostgreSQL: run mysqldump / pg_dump (see README).')
        return None
    src_path = DB_URL.replace('sqlite:///', '')
    folder = os.path.join(DATA_DIR, 'backups')
    os.makedirs(folder, exist_ok=True)
    dst_path = os.path.join(folder, 'attendance_%s.db' % time.strftime('%Y%m%d_%H%M'))
    src, dst = sqlite3.connect(src_path), sqlite3.connect(dst_path)
    with dst:
        src.backup(dst)                                 # consistent snapshot even while users are working
    src.close()
    dst.close()
    for old in sorted(glob.glob(os.path.join(folder, 'attendance_*.db')))[:-KEEP]:
        os.remove(old)
    return dst_path


if __name__ == '__main__':
    print('Backup saved:', backup_sqlite())
