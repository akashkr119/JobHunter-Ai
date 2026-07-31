import sqlite3
from pathlib import Path

class Database:
    def __init__(self, db_path='jobs.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def execute(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def fetchall(self, query, params=()):
        return self.execute(query, params).fetchall()

    def close(self):
        self.conn.close()
