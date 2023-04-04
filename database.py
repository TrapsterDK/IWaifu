import threading
import sqlite3
from pathlib import Path
from abc import abstractmethod
import datetime


# This is a thread-safe wrapper around sqlite3, which also supports periodic backups
class ThreadSafeDB:
    con: sqlite3.Connection = None
    backup_dir: Path = None
    db_file: str = None
    write_lock: threading.Lock = None
    backup_interval: int = None
    backup_thread: threading.Timer = None
    backup_dir: Path = None

    def __init__(
        self, db_file: Path, backup_dir: Path = None, backup_interval_ms: int = 3600
    ):
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.con = sqlite3.connect(
            db_file, check_same_thread=False, isolation_level="DEFERRED"
        )
        self.con.execute("PRAGMA journal_mode=WAL2")
        self.con.row_factory = sqlite3.Row

        self.db_file = db_file
        self.write_lock = threading.Lock()

        if backup_dir is not None:
            self.backup_dir = backup_dir
            self.backup_interval = backup_interval_ms
            self.backup_thread = threading.Timer(self.backup_interval, self._backup)
            self.backup_thread.start()

        self.create_tables()

    def _backup(self):
        if self.backup_dir is None:
            return

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        backup_file = (
            self.backup_dir
            / f"{self.db_file.stem}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )

        backup_con = sqlite3.connect(backup_file)
        with self.write_lock:
            self.con.backup(backup_con)

        self.backup_thread = threading.Timer(self.backup_interval, self._backup)
        self.backup_thread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.con.rollback()
        else:
            self.con.commit()
        self.close()

    def close(self):
        if self.backup_thread is not None:
            self.backup_thread.cancel()
        self.con.close()

    def __del__(self):
        self.close()

    @abstractmethod
    def create_tables(self):
        pass
