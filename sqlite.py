import sqlite3
from password import generate_salt, hash_password
from threading import Lock


class Database:
    def __init__(self, db_file):
        self.db_file = db_file

        self.con = sqlite3.connect(db_file, check_same_thread=False)
        self.con.execute("PRAGMA journal_mode=WAL")

        self.con.row_factory = sqlite3.Row
        self.lock = Lock()

        self.create_tables()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.con.close()

    def close(self):
        self.con.close()

    # create all tables
    def create_tables(self):
        c = self.con.cursor()

        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            salt BLOB NOT NULL
        )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS waifus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            waifu_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            from_user INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
            FOREIGN KEY (waifu_id) REFERENCES waifus (id)
        )"""
        )

        c.execute(
            """CREATE INDEX IF NOT EXISTS messages_user_id_index ON messages (user_id)"""
        )

        c.execute(
            """CREATE INDEX IF NOT EXISTS messages_waifu_id_index ON messages (waifu_id)"""
        )

        self.con.commit()

    # returns the user id if the user was added, otherwise returns None
    def add_user(self, username: str, password: str, email: str) -> bool:
        if self.username_exists(username) or self.email_exists(email):
            return None

        salt = generate_salt()
        hashed_password = hash_password(password, salt)

        with self.lock:
            c = self.con.cursor()
            c.execute(
                "INSERT INTO users (username, password, email, salt) VALUES (?, ?, LOWER(?), ?)",
                (username, hashed_password, email, salt),
            )

            self.con.commit()

            return c.lastrowid

    # returns True if the user exists and the password is correct, otherwise returns False
    def verify_user(self, email: str, password: str) -> bool:
        with self.lock:
            c = self.con.cursor()
            c.execute("SELECT * FROM users WHERE email = LOWER(?)", (email,))
            user = c.fetchone()

        if user is None:
            return False

        salt = user["salt"]
        hashed_password = hash_password(password, salt)
        if hashed_password != user["password"]:
            return False

        return True

    # returns true if the username exists, otherwise returns false
    def username_exists(self, username: str) -> int or bool:
        with self.lock:
            c = self.con.cursor()
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_id = c.fetchone()

        if user_id is None:
            return False

        return True

    # returns true if the email exists, otherwise returns false
    def email_exists(self, email: str) -> bool:
        with self.lock:
            c = self.con.cursor()
            c.execute("SELECT id FROM users WHERE email = LOWER(?)", (email,))
            user_id = c.fetchone()

        if user_id is None:
            return False

        return True

    # returns the user if the user exists, otherwise returns None
    def get_email_user(self, email: str) -> dict or None:
        with self.lock:
            c = self.con.cursor()
            c.execute("SELECT * FROM users WHERE email = LOWER(?)", (email,))
            user = c.fetchone()

        if user is None:
            return None

        return user

    # returns the user if the user exists, otherwise returns None
    def get_user(self, user_id: int) -> dict or None:
        with self.lock:
            c = self.con.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = c.fetchone()

        if user is None:
            return None

        return user

    def get_user_from_email(self, email: str) -> dict or None:
        with self.lock:
            c = self.con.cursor()
            c.execute("SELECT * FROM users WHERE email = LOWER(?)", (email,))
            user = c.fetchone()

        if user is None:
            return None

        return user

    def add_waifu(self, name: str) -> int or None:
        waifu_id = self.get_waifu_id(name)
        if waifu_id is not None:
            return waifu_id

        with self.lock:
            c = self.con.cursor()
            c.execute("INSERT INTO waifus (name) VALUES (?)", (name,))
            self.con.commit()

        return c.lastrowid

    def get_waifu_id(self, name: str) -> int or None:
        with self.lock:
            c = self.con.cursor()
            c.execute("SELECT id FROM waifus WHERE name = ?", (name,))
            waifu_id = c.fetchone()

        if waifu_id is None:
            return None

        return waifu_id["id"]

    def add_message(
        self, user_id: int, waifu_id: int, message: str, from_user: bool, timestamp: int
    ):
        with self.lock:
            c = self.con.cursor()
            c.execute(
                "INSERT INTO messages (user_id, waifu_id, message, timestamp, from_user) VALUES (?, ?, ?, ?, ?)",
                (user_id, waifu_id, message, timestamp, from_user),
            )

            self.con.commit()

    def get_messages(self, user_id: int, waifu_id: int, limit: int) -> list:
        with self.lock:
            c = self.con.cursor()
            c.execute(
                "SELECT * FROM messages WHERE user_id = ? AND waifu_id = ? ORDER BY timestamp ASC LIMIT ?",
                (user_id, waifu_id, limit),
            )
            messages = c.fetchall()

        return messages
