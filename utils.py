
import hashlib
import os
import ffmpeg

def generate_salt() -> str:
    return os.urandom(32).hex()

def hash_password(plaintext: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', plaintext, salt, 10000)

def mp4_to_wav(mp4_file: str, wav_file: str):
    stream = ffmpeg.input(mp4_file)
    stream = ffmpeg.output(stream, wav_file)
    ffmpeg.run(stream, quiet=True)
