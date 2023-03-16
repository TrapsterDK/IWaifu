import sqlite3
from flask import current_app, g
from utils import hash_password, generate_salt

class SQLite:
    def __init__(self, db_file):
        self.db_file = db_file
        self.db = sqlite3.connect(current_app.config['DATABASE'])
        self.db.row_factory = sqlite3.Row
        self.conn = self.db.cursor()


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()


    def close(self):
        self.db.close()


    # create all tables
    def create_tables(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            salt TEXT NOT NULL,
        )''')


    # returns True if the user was added, otherwise returns False
    def add_user(self, username: str, password: str) -> bool:
        if self.get_username_id(username) != None:
            return False
        
        salt = generate_salt()
        hashed_password = hash_password(password, salt)
        self.conn.execute('INSERT INTO users (username, password, salt) VALUES (?, ?, ?)', (username, hashed_password, salt))
        self.db.commit()

        return True


    # returns True if the user exists and the password is correct, otherwise returns False
    def verify_user(self, username: str, password: str) -> bool:
        self.conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = self.conn.fetchone()
        if user is None:
            return False
        
        salt = user['salt']
        hashed_password = hash_password(password, salt)
        if hashed_password != user['password']:
            return False

        return True


    # returns the user id if the user exists, otherwise returns None
    def get_username_id(self, username: str) -> int or None:
        self.conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = self.conn.fetchone()
        if user is None:
            return None
        
        return user['id']
        
    

def get_db() -> SQLite:
    if 'db' not in g:
        g.db = SQLite(current_app.config['DATABASE'])

    return g.db


def close_db(e=None) -> None:
    db = g.pop('db', None)

    if db is not None:
        db.close()
