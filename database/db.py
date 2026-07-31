import sqlite3

class Database:
    def __init__(self, db_path='jobs.db'):
        self.db_path=db_path
        self.conn=sqlite3.connect(db_path)
    def connect(self):
        return self.conn
    def execute(self,query,params=()):
        cur=self.conn.cursor();cur.execute(query,params);self.conn.commit();return cur
    def fetchall(self,query,params=()):
        return self.execute(query,params).fetchall()
    def save_job(self,job):
        return job
    def close(self):
        self.conn.close()