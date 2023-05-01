import sqlite3


class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.db = sqlite3.connect(db_file)
        self.db.row_factory = sqlite3.Row
        self.conn = self.db.cursor()

        self.create_tables()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def close(self):
        self.db.close()

    # create all tables
    def create_tables(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            salt BLOB NOT NULL
        )"""
        )

        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )"""
        )

        self.conn.execute(
            """CREATE INDEX IF NOT EXISTS messages_user_id_index ON messages (user_id)"""
        )

    # returns the user id if the user was added, otherwise returns None
    def add_user(self, username: str, password: str, email: str) -> bool:
        if self.username_exists(username) or self.email_exists(email):
            return None

        salt = generate_salt()
        hashed_password = hash_password(password, salt)
        self.conn.execute(
            "INSERT INTO users (username, password, email, salt) VALUES (?, ?, ?, ?)",
            (username, hashed_password, email, salt),
        )

        self.db.commit()

        return self.conn.lastrowid

    # returns True if the user exists and the password is correct, otherwise returns False
    def verify_user(self, email: str, password: str) -> bool:
        self.conn.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = self.conn.fetchone()
        if user is None:
            return False

        salt = user["salt"]
        hashed_password = hash_password(password, salt)
        if hashed_password != user["password"]:
            return False

        return True

    # returns true if the username exists, otherwise returns false
    def username_exists(self, username: str) -> int or bool:
        self.conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = self.conn.fetchone()
        if user_id is None:
            return False

        return True

    # returns true if the email exists, otherwise returns false
    def email_exists(self, email: str) -> bool:
        self.conn.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = self.conn.fetchone()
        if user_id is None:
            return False

        return True

    # returns the user if the user exists, otherwise returns None
    def get_email_user(self, email: str) -> dict or None:
        self.conn.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = self.conn.fetchone()
        if user is None:
            return None

        return user

    # returns the user if the user exists, otherwise returns None
    def get_user(self, user_id: int) -> dict or None:
        self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = self.conn.fetchone()
        if user is None:
            return None

        return user
