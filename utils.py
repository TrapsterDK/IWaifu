
import hashlib
import os
import ffmpeg
import pathlib
import threading
import json
from typing import Any

BASE_PATH = pathlib.Path("D:/iwaifudata/")
FOLDER_DOWNLOAD_MP4 = BASE_PATH / "mp4"
FOLDER_DOWNLOAD_MP3 = BASE_PATH / "mp3"

def generate_salt() -> str:
    return os.urandom(32).hex()

def hash_password(plaintext: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', plaintext, salt, 10000)

def mp4_to_mp3(mp4_file: pathlib.Path, mp3_file: pathlib.Path):
    stream = ffmpeg.input(str(mp4_file))
    stream = ffmpeg.output(stream, str(mp3_file))

    try:
        ffmpeg.run(stream, quiet=True)
    except ffmpeg.Error as e:
        raise e
    

class Log:
    def __init__(self, filename: pathlib.Path or str, processed_hook=None, error_hook=None):
        self.filename = filename
        self.lock = threading.Lock()
        self.entry_hook = processed_hook
        self.error_hook = error_hook

        try:
            with open(self.filename, "r") as f:
                self.log = json.load(f)
        except FileNotFoundError:
            self.log = {"processed": {}, "errors": {}, "entries": {}}

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        with open(self.filename, "w") as f:
            json.dump(self.log, f)

    def write_entry(self, key: str):
        with self.lock:
            self.log["entries"][key] = None

    def write_error(self, key: str, error: str):
        with self.lock:
            self.log["errors"][key] = error
            if self.error_hook is not None:
                self.error_hook(key, error)

    def move_to_processed(self, key: str, value: Any):
        with self.lock:
            self.log["processed"][key] = value
            del self.log["entries"][key] 

    def get_processed(self) -> dict:
        return self.log["processed"]
    
    def get_errors(self) -> dict:
        return self.log["errors"]
    
    def get_entries(self) -> dict:
        return self.log["entries"]
    