import mariadb
import sys


class SQLManager:

    def __init__(self):
        try: 
            conn = mariadb.connect(
                user="root",
                password="toor",
                host="localhost",
                port=3306
            )
        except mariadb.Error as e:
            print(f"Database Error: {e}")
            sys.exit(1)

        self.cur = conn.cursor()

    def execute(self, command, variables=None):
        if variables:
            self.cur.execute(command, (variables,))
        else:
            self.cur.execute(command)

if __name__ == "__main__":
    s = SQLManager()
    s.execute("CREATE DATABASE test")