
import hashlib
import os
import ffmpeg
from pathlib import Path

def generate_salt() -> str:
    return os.urandom(32).hex()

def hash_password(plaintext: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', plaintext, salt, 10000)

def mp4_to_mp3(mp4_file: Path, mp3_file: Path):
    stream = ffmpeg.input(str(mp4_file))
    stream = ffmpeg.output(stream, str(mp3_file))

    print(str(mp4_file), str(mp3_file))
    try:
        ffmpeg.run(stream, quiet=True)
    except ffmpeg.Error as e:
        raise e
    
LOG_SEPARATOR = " : "
LOG_ERROR = "E"
LOG_SUCCESS = "S"
def file_log_write(file_handle, filename: str, error=False, info=None):
    write = filename + LOG_SEPARATOR + LOG_ERROR if error else LOG_SUCCESS
    if info:
        write += LOG_SEPARATOR + info
    file_handle.write(write)

def file_log_read(file_handle):
    for line in file_handle:
        line = line.split(LOG_SEPARATOR)
        yield line[0], line[1], line[2] if len(line) == 3 else None

def file_log_get_errors(file_handle):
    for line in file_log_read(file_handle):
        if line[1] == LOG_ERROR:
            yield line

def file_log_get_successes(file_handle):
    for line in file_log_read(file_handle):
        if line[1] == LOG_SUCCESS:
            yield line