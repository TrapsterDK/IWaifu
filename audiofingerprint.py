import dejavu
import pydub
from pathlib import Path
from database import ThreadSafeDB
from multiprocessing import Pool
from multiprocessing.managers import BaseManager
import tqdm
from functools import partial
import signal
import platform


class FingerPrintDatabase(ThreadSafeDB):
    def __init__(
        self, db_file: Path, backup_dir: Path = None, backup_interval_ms: int = 3600
    ):
        super().__init__(db_file, backup_dir, backup_interval_ms)
        # https://www.sqlite.org/pragma.html#pragma_synchronous
        self.con.execute("""PRAGMA synchronous = OFF""")
        self.con.execute("""PRAGMA cache_size = 1000000""")
        self.con.execute("""PRAGMA locking_mode = EXCLUSIVE""")
        self.con.execute("""PRAGMA temp_store = MEMORY""")

    def create_tables(self):
        self.con.execute(
            """CREATE TABLE IF NOT EXISTS fingerprints (
            hash BLOB NOT NULL,
            audio_id INTEGER NOT NULL,
            offset INTEGER NOT NULL,
            PRIMARY KEY (hash, audio_id, offset)
        )"""
        )

        self.con.execute(
            """CREATE TABLE IF NOT EXISTS audios (
            audio_id INTEGER PRIMARY KEY AUTOINCREMENT,
            audio_name TEXT NOT NULL UNIQUE,
            fingerprinted BOOLEAN NOT NULL DEFAULT 0
        )"""
        )

        self.con.execute(
            """CREATE INDEX IF NOT EXISTS hash_index ON fingerprints (hash)"""
        )

    def insert_fingerprint(self, hash: bytes, offset_s: int, audio_id: int):
        self.insert_fingerprints([(hash, offset_s)], audio_id)

    def insert_fingerprints(self, hashes: list[tuple[bytes, int]], audio_id: int):
        c = self.con.cursor()

        with self.write_lock:
            c.executemany(
                "INSERT INTO fingerprints VALUES (?, ?, ?)",
                [(hash, audio_id, offset) for hash, offset in hashes],
            )
            self.con.commit()

    def insert_audio(self, audio_name: str) -> int:
        c = self.con.cursor()

        c.execute("SELECT audio_id FROM audios WHERE audio_name = ?", (audio_name,))
        fetch = c.fetchone()
        if fetch is not None:
            return fetch["audio_id"]

        with self.write_lock:
            c.execute("INSERT INTO audios (audio_name) VALUES (?)", (audio_name,))
            self.con.commit()

        return c.lastrowid

    def audio_set_fingerprinted(self, audio_id: int):
        c = self.con.cursor()

        with self.write_lock:
            c.execute(
                "UPDATE audios SET fingerprinted = 1 WHERE audio_id = ?", (audio_id,)
            )
            self.con.commit()

    def audio_is_fingerprinted(self, audio_name: str) -> bool:
        c = self.con.cursor()

        c.execute(
            "SELECT fingerprinted FROM audios WHERE audio_name = ?", (audio_name,)
        )
        fetch = c.fetchone()

        if fetch is None:
            return False

        return fetch["fingerprinted"] == 1


def fingerprint_file(file: Path, db: FingerPrintDatabase):
    if not file.is_file():
        return

    if db.audio_is_fingerprinted(file.name):
        return

    audio_id = db.insert_audio(file.name)

    audio = pydub.AudioSegment.from_file(file, file.suffix[1:])

    hashes = dejavu.fingerprint(audio.get_array_of_samples())

    db.insert_fingerprints(hashes, audio_id)

    db.audio_set_fingerprinted(audio_id)


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def fingerprint_folder(folder: Path, database_manager: FingerPrintDatabase):
    folders_len = len(list(folder.iterdir()))

    print(f"Fingerprinting {folders_len} files")

    with Pool(2, initializer=init_worker) as pool:
        try:
            for _ in tqdm.tqdm(
                pool.imap_unordered(
                    partial(fingerprint_file, db=database_manager), folder.iterdir()
                ),
                total=folders_len,
            ):
                pass

        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, terminating workers")
            pool.terminate()
            pool.join()
        else:
            print("Fingerprinting done")
            pool.close()


def fingerprint_folder_single_threaded(folder: Path, db: FingerPrintDatabase):
    folders_len = len(list(folder.iterdir()))

    print(f"Fingerprinting {folders_len} files")

    for file in tqdm.tqdm(folder.iterdir(), total=folders_len):
        fingerprint_file(file, db)

    print("Fingerprinting done")


# multthreaded fingerprinting
if __name__ == "__main__":
    MULTITHREADED = False
    print(f"Multithreaded: {MULTITHREADED}")

    if platform.uname().system == "Windows":
        db_path = Path("D:/iwaifudata/audio_fingerprints.db")
        backup_dir = Path("D:/iwaifudata/backup/audio_fingerprints")
        mp3_dir = Path("D:/iwaifudata/mono_mp3")
    else:
        db_path = Path("/mnt/d/iwaifudata/audio_fingerprints.db")
        backup_dir = Path("/mnt/d/iwaifudata/backup/audio_fingerprints")
        mp3_dir = Path("/mnt/d/iwaifudata/mono_mp3")

    if MULTITHREADED:
        BaseManager.register("FingerPrintDatabase", FingerPrintDatabase)

        with BaseManager() as manager:
            db = manager.FingerPrintDatabase(
                db_path,
                backup_dir,
            )

            fingerprint_folder(mp3_dir, db)

            db.close()
    else:
        with FingerPrintDatabase(
            db_path,
            backup_dir,
        ) as db:
            try:
                fingerprint_folder_single_threaded(mp3_dir, db)
            except KeyboardInterrupt:
                print("Caught KeyboardInterrupt")
