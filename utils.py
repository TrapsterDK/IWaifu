import hashlib
import os
import ffmpeg
import pathlib
import json
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import multiprocessing
import sys
import traceback


BASE_PATH = pathlib.Path("D:/iwaifudata/")
FOLDER_DOWNLOAD_MP4 = BASE_PATH / "mp4"
FOLDER_DOWNLOAD_MP3 = BASE_PATH / "mp3"
FOLDER_LOGS = BASE_PATH / "logs"

LOG_ANIMES = FOLDER_LOGS / "animes.json"
LOG_EPISODES = FOLDER_LOGS / "episodes.json"
LOG_MP4 = FOLDER_LOGS / "mp4.json"
LOG_MP3 = FOLDER_LOGS / "mp3.json"

def generate_salt() -> str:
    return os.urandom(32).hex()

def hash_password(plaintext: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', plaintext, salt, 10000)

def mp4_to_mp3(mp4_file: pathlib.Path, mp3_file: pathlib.Path):
    stream = ffmpeg.input(str(mp4_file))
    stream = ffmpeg.output(stream, str(mp3_file))

    ffmpeg.run(stream, quiet=True, overwrite_output=True)
    

class Log:
    def __init__(self, filename: pathlib.Path or str):
        self.filename = filename
        self.lock = multiprocessing.Lock()

        try:
            with open(self.filename, "r") as f:
                self.log = json.load(f)
        except FileNotFoundError:
            self.log = {
                "processed": {}, 
                "errors": {}, 
                "entries": {}, 
                "processed_read": {},
            }

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.log, f)

    def write_entry(self, key: str):
        self.write_entries([key])

    def write_entries(self, keys: list):
        if len(keys) == 0:
            return
        
        with self.lock:
            for key in keys:
                self.log["entries"][key] = None

    def write_error(self, key: str, error: str):
        with self.lock:
            self.log["errors"][key] = error

    def write_processed(self, key: str, value: Any):
        with self.lock:
            if key not in self.log["entries"]:
                self.save()
                raise KeyError(f"Key {key} not found in entries")
            
            self.log["processed"][key] = value
            del self.log["entries"][key] 

    def get_processed(self) -> dict:
        with self.lock:
            values = [value for value in self.log["processed"].values()]
            self.log["processed_read"].update(self.log["processed"])
            self.log["processed"] = {}

            values_unwrapped = []
            for value in values:
                if isinstance(value, list):
                    values_unwrapped.extend(value)
                else:
                    values_unwrapped.append(value)

            return values_unwrapped
    
    def get_errors(self) -> dict:
        with self.lock:
            return self.log["errors"]

    def get_entries(self) -> dict:
        with self.lock:
            return self.log["entries"]

def ThreadPoolWithLog(console_name: str, log: Log, listen_log: Log,  function: partial, max_workers=5):
    print(f"{console_name}: Starting with {max_workers} workers")
    sys.stdout.flush()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        entries = log.get_entries()
        futures = {key: executor.submit(function, key) for key in entries.keys()}

        while True:
            new_items = listen_log.get_processed()
            log.write_entries(new_items)
            for new_item in new_items:
                futures[new_item] = executor.submit(function, new_item)

            if len(new_items) > 0:
                print(f"{console_name}: Waiting for {len(futures)} futures")
                sys.stdout.flush()
            
            try:
                for key in futures.keys():
                    future = futures[key]
                    if future.done():
                        try:
                            value = future.result()
                        except Exception as e:
                            print(f"{console_name}: Error processing {key}: {e}")
                            sys.stdout.flush()
                            log.write_error(key, str(e))
                            log.save()
                        else:
                            log.write_processed(key, value)
                        #finally:
                            #del futures[key]

                        print(f"{console_name}: Waiting for {len(futures)} futures")
                        sys.stdout.flush()

            except Exception as e:
                print(f"{console_name}: Error: {e}")
                tb = traceback.format_exc()
                print("tb:", tb)
                sys.stdout.flush()
                log.save()
                break