import mariadb
import sys
import configparser
import re

class SQLManager:

    def __init__(self):
        cfg = configparser.ConfigParser()
        cfg.read("config.ini")
        self.USER = cfg["DATABASE"]["user"]
        self.PASSWORD = cfg["DATABASE"]["password"]
        self.HOST = cfg["DATABASE"]["host"]
        try:
            self.PORT = int(cfg["DATABASE"]["port"])
        except TypeError:
            print("Improper port in config file: Non-integer character")
            sys.exit(1)

    def create_connection(self, database:str):
        try:
            conn = mariadb.connect(
                user=self.USER,
                password=self.PASSWORD,
                host=self.HOST,
                port=self.PORT,
                database=database
            )

        except mariadb.Error as e:
            print(f"Database error: {e}")
            sys.exit(1)

        return conn

    #DANGEROUS FUNCTION!!!
    #WILL BE DEPRECIATED LATER
    def execute(self, command, variables=None):
        conn = self.create_connection("test")
        cur = conn.cursor()
        if variables:
            cur.execute(command, (variables,))
        else:
            cur.execute(command)

        conn.close()

    #Takes in a list of columns and a table, returns all information from the select statement.
    #Defaults to the test database.
    #where_conditions should be formatted as a dictionary.
    #For example, if you're selecting from the column of player names where name = "notch";
    #where_conditions = {"name" : "Notch"}

    #Doesn't support OR statements yet
    def select(self, columns:list, table:str, where_conditions=None, database="test"):

        #First remove everything except letters/numbers (and the all character) from column names
        safe_columns = []
        safe_columns_string = ""
        index = 0
        for column in columns:
            sanitized = re.sub(r"^0-9A-Za-z*", "", column)
            safe_columns.append(sanitized)
            if index < len(columns)-1:
                safe_columns_string = safe_columns_string + sanitized + ", "
            else:
                safe_columns_string = safe_columns_string + sanitized

            index += 1

        #Make sure the table variable is safe too
        safe_table = re.sub(r"^0-9A-Za-z*", "", table)

        sql = f"SELECT {safe_columns_string} FROM {safe_table}"
        
        if where_conditions:
            #Gotta sanitize the conditions too
            safe_keys = []
            for key in where_conditions.keys():
                safe_key = re.sub(r"^0-9A-Za-z", "", key)
                safe_keys.append(safe_key)


            sql += " WHERE ".join("f{safe_keys[0]}=?")
            
            #TODO:
            #Implement OR statements
            if len(safe_keys > 1):
                for key in safe_keys[1:]:
                    sql += " AND ".join("f{key}=?")

            #and the paramaters
            safe_values = []
            for value in where_conditions.values():
                safe_value = re.sub(r"^0-9A-Za-z", "", value)
                safe_values.append(safe_value)

            params = safe_values

        try:
            #Create a connection, fetch the cursor/data, close the connection and return results
            conn = self.create_connection(database)
            cur = conn.cursor()
            cur.execute(sql, params)
            results = cur.fetchall()
        except mariadb.Error as e:
            print(f"Database error in select statement: {e}")
        finally:
            if conn:
                conn.close()
        return results





#Only runs when this py file is run by itself
if __name__ == "__main__":
    s = SQLManager()
    s.execute("CREATE DATABASE test")
