import hashlib
import os


def generate_salt() -> bytes:
    return os.urandom(32)


def hash_password(plaintext: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", plaintext.encode("utf-8"), salt, 100000)
