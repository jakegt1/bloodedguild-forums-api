import psycopg2
from psycopg2.extras import DictCursor


class DatabaseConnector():
    db_settings = {}

    def __init__(self):
        self.open()

    @classmethod
    def add_settings(cls, settings):
        cls.db_settings = settings

    def get_conn_string(self):
        return str(self.db_string_constructor)

    def get_cursor(self):
        return self.connection.cursor()

    def rollback(self):
        self.connection.rollback()
        self.connection.close()

    def close(self):
        self.connection.commit()
        self.connection.close()

    def open(self):
        self.connection = psycopg2.connect(
            cursor_factory=DictCursor,
            **self.db_settings
        )


class DatabaseAuth():
    def __init__(self):
        self.db = DatabaseConnector()

    def check_auth(self, username, password):
        psql_cursor = self.db.get_cursor()
        sql_string = "select id, username, name, privilege "
        sql_string += "from users_post_counts "
        sql_string += "where username = %s"
        sql_string += "and password_hash = crypt(%s, password_hash);"
        psql_cursor.execute(
            sql_string,
            (username, password)
        )
        query_result = psql_cursor.fetchone()
        psql_cursor.close()
        self.db.close()
        return query_result

