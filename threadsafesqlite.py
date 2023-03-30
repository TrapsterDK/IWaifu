import time
import threading
import sqlite3
from pathlib import Path

# This is a thread-safe wrapper around sqlite3, which also supports periodic backups
class ThreadSafeDB:
    def __init__(self, db_file: str, backup_dir: Path=None, backup_interval_ms: int=3600):
        self.con = sqlite3.connect(db_file, check_same_thread=False)
        self.con.execute('PRAGMA journal_mode=WAL')

        self.backup_dir = backup_dir
        self.db_file = db_file
        self.write_lock = threading.Lock()

        if self.backup_dir is not None:
            # Backup every hour
            self.backup_interval = backup_interval_ms
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.backup_thread = threading.Timer(self.backup_interval, self.backup)
            self.backup_thread.start()

    def backup(self):
        if self.backup_dir is None:
            return
        
        backup_file = self.backup_dir / f'{self.db_file}_{time.time()}.db'
        with self.write_lock:
            self.con.backup(backup_file)

        self.backup_thread = threading.Timer(self.backup_interval, self.backup)
        self.backup_thread.start()

    def __enter__(self):
        return self.con

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.con.rollback()
        else:
            self.con.commit()
        self.close()

    def close(self):
        self.backup_thread.cancel()
        self.con.close()
    
    def __del__(self):
        self.close()

    