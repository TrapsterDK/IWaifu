import hashlib
import os
import pathlib
import json
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import multiprocessing
import sys
import time
import shutil
from moviepy.editor import VideoFileClip
import signal

BASE_PATH = pathlib.Path("D:/iwaifudata/")
FOLDER_DOWNLOAD_MP4 = BASE_PATH / "mp4"
FOLDER_DOWNLOAD_MP3 = BASE_PATH / "mp3"
FOLDER_LOGS = BASE_PATH / "logs"

LOG_ANIMES = FOLDER_LOGS / "animes.json"
LOG_EPISODES = FOLDER_LOGS / "episodes.json"
LOG_MP4 = FOLDER_LOGS / "mp4.json"
LOG_MP3 = FOLDER_LOGS / "mp3.json"

MINUTES_SAVE_LOG = 2
MINUTE = 60

def generate_salt() -> bytes:
    return os.urandom(32)

def hash_password(plaintext: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', plaintext.encode('utf-8'), salt, 100000)

def mp4_to_mp3(mp4_file: pathlib.Path, mp3_file: pathlib.Path):
    video = VideoFileClip(str(mp4_file))
    audio = video.audio
    audio.write_audiofile(str(mp3_file), logger=None)
    video.close()

def file_increment(path: pathlib.Path) -> int:
    i = 1
    while path.with_name(f"{path.stem} ({i}){path.suffix}").exists():
        i += 1

    return i

def file_increment_name(path: pathlib.Path, i: int) -> pathlib.Path:
    return path.with_name(f"{path.stem} ({i}){path.suffix}")
        


class Log:
    def __init__(self, filename: pathlib.Path or str):
        self.filename = filename
        self.filename_error = self.filename.with_suffix(".error.json")
        self.lock = multiprocessing.Lock()

        if self.filename.exists():
            with open(self.filename, "r") as f:
                self.log = json.load(f)
        else:
            self.log = {}

        if self.filename_error.exists():
            with open(self.filename_error, "r") as f:
                self.log_error = json.load(f)
        else:
            self.log_error = {}

    # only one thread should write to the log
    def save(self):
        directory = self.filename.parent

        # get the current stored log
        if self.filename.exists():
            with open(self.filename, "r") as f:
                old_log = json.load(f)
        else:
            old_log = None

        if self.filename_error.exists():
            with open(self.filename_error, "r") as f:
                old_log_error = json.load(f)
        else:
            old_log_error = None

        # if the log has changed, save the old log and save the new log
        if (old_log != None and old_log_error != None and 
            (old_log != self.log or old_log_error != self.log_error)):
            # create the old folder if it doesn't exist
            directory_old = directory / "old"
            directory_old.mkdir(exist_ok=True)

            # get the old log file name by finding the highest number in the old folder of the same name
            old_filename_i = file_increment(directory_old / self.filename.name)
            old_filename_error_i = file_increment(directory_old / self.filename_error.name)
            max_i = max(old_filename_i, old_filename_error_i)

            old_filename = file_increment_name(directory_old / self.filename.name, max_i)
            old_filename_error = file_increment_name(directory_old / self.filename_error.name, max_i)

            # move the old log to the old folder
            shutil.move(self.filename, old_filename)
            shutil.move(self.filename_error, old_filename_error)

        # save the new log
        with open(self.filename, "w") as f:
            json.dump(self.log, f)

        with open(self.filename_error, "w") as f:
            json.dump(self.log_error, f)

    def write_tasks(self, keys: list[str]):
        with self.lock:
            for key in keys:
                assert key not in self.log_error
                assert key not in self.log
                assert type(key) is str

                self.log[key] = None

    def write_task_done(self, key: str, value: Any):
        with self.lock:
            assert key in self.log
            assert self.log[key] is None
            
            assert value is not None
            assert type(value) is list or type(value) is str

            self.log[key] = value

    def write_error(self, key: str, error: str):
        with self.lock:
            assert key in self.log
            assert self.log[key] is None
                
            assert type(key) is str
            assert error is not None
            assert type(error) is str

            del self.log[key]
            self.log_error[key] = error

    def get_values(self):
        with self.lock:
            values_unpacked = []
            for value in self.log.values():
                if value is None:
                    continue
                
                if type(value) is list:
                    values_unpacked.extend(value)
                    continue

                if type(value) is str:
                    values_unpacked.append(value)
                    continue

                raise Exception(f"Unknown value type: {type(value)} {type(value) is list}")

            return values_unpacked
        
    def get_all_keys(self):
        with self.lock:
            return list(self.log.keys()) + list(self.log_error.keys())

    def get_none_keys(self):
        with self.lock:
            return [key for key, value in self.log.items() if value is None]
        
    def keys_not_in_log(self, keys: list):
        self_keys = self.get_all_keys()
        with self.lock:
            return list(set(keys).difference(set(self_keys)))


def ThreadPoolRunOnLog(listen_log: Log, write_log: Log, function: partial, done: multiprocessing.Value, max_workers=5):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    process_name = multiprocessing.current_process().name
    print(f"Starting {process_name}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # start the futures for the entries that are alredy in the write log
        keys = write_log.get_none_keys()
        futures = {key: executor.submit(function, key) for key in keys}
        del keys
    
        last_save = time.time()

        while True:
            # get the new items from the listen log
            new_items = write_log.keys_not_in_log(listen_log.get_values())
            write_log.write_tasks(new_items)
            for new_item in new_items:
                futures[new_item] = executor.submit(function, new_item)

            if len(new_items) > 0:
                print(f"{process_name}: Waiting for {len(futures)} futures")
            
            # check if the futures are done
            for key in list(futures.keys()):
                future = futures[key]
                if future.done():
                    del futures[key]
                    try:
                        value = future.result()
                        write_log.write_task_done(key, value)
                    except Exception as e:
                        write_log.write_error(key, str(e))
                        print(f"{process_name}: Error: {e}")

                    
                    print(f"{process_name}: Waiting for {len(futures)} futures")

            # check if the program should exit
            if done.value == True:
                break
            
            time.sleep(1)

            # save the log every 2 minutes
            if time.time() - last_save > MINUTES_SAVE_LOG * MINUTE:
                write_log.save()
                last_save = time.time()

        # save the log when the program exits
        write_log.save()

        print(f"Exiting {process_name}")
        
        # immediately exit the program
        os._exit(0)

