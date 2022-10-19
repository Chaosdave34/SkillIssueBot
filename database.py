import sqlite3


class DatabaseHandler:
    def __init__(self):
        self.connection = sqlite3.connect("database.db")
        self.cursor = self.connection.cursor()

        self._initialize()

    def _initialize(self):
        sql = "CREATE TABLE IF NOT EXISTS inactivity(id TEXT PRIMARY_KEY, last_message REAL, last_voice REAL);"
        self.cursor.execute(sql)
        sql = "CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY_KEY, uuid TEXT);"
        self.cursor.execute(sql)
        self.connection.commit()

    # Inactivity Table
    def check_user_inactivity(self, user_id):
        sql = f"SELECT id FROM inactivity WHERE id = '{user_id}';"
        self.cursor.execute(sql)
        if not self.cursor.fetchone():
            sql = f"INSERT INTO inactivity VALUES('{user_id}', null, null);"
            self.cursor.execute(sql)
            self.connection.commit()

    def update_user_inactivity(self, user_id, last_message=None, last_voice=None):
        if last_message:
            sql = f"UPDATE inactivity SET last_message = {last_message} WHERE id = '{user_id}';"
            self.cursor.execute(sql)
        if last_voice:
            sql = f"UPDATE inactivity SET last_voice = {last_voice} WHERE id = '{user_id}';"
            self.cursor.execute(sql)
        self.connection.commit()

    def get_all_user_inactivity(self):
        sql = "SELECT * FROM inactivity;"
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        return data

    def get_user_inactivity(self, user_id):
        sql = f"SELECT * FROM inactivity WHERE id = '{user_id}';"
        self.cursor.execute(sql)
        data = self.cursor.fetchone()
        return data

    # Users Table
    def check_user(self, member_id):
        sql = f"SELECT id FROM users WHERE id = '{member_id}';"
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    def add_user(self, member_id, uuid):
        sql = f"INSERT INTO users VALUES('{member_id}', '{uuid}');"
        self.cursor.execute(sql)
        self.connection.commit()

