import mariadb
import sys
import configparser
import re

#https://mariadb-corporation.github.io/mariadb-connector-python/cursor.html
#Important API doc

#There are a few better implementations of the API from what I can tell
#Not too sure if theyre necessary to implement but we can look into it down the road

#TODO:
#Update all re.sub functions to ''.join(filter(str.isalpha, string)) (roughly 2x as fast)
#Add DELETE functions other than just dropping the whole table

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

        #Note: Database name is loaded from config file
        #May want to add option to be passed into constructor
        self.DATABASE = cfg["DATABASE"]["database"]

    def create_connection(self):
        try:
            conn = mariadb.connect(
                user=self.USER,
                password=self.PASSWORD,
                host=self.HOST,
                port=self.PORT,
                database=self.DATABASE
            )

        except mariadb.Error as e:
            print(f"Database error: {e}")
            sys.exit(1)

        return conn
    #Resets test database to a default state, containing a single fake ticket.
    def reset_to_default(self):
        try:
            data = [("id", "int"), ("event", "varchar(255)"), ("uuid", "varchar(255)"), ("discordID", "varchar(255)"), ("message", "varchar(255)")]
            #Create a connection, fetch the cursor/data, close the connection and return results
            conn = self.create_connection()
            cur = conn.cursor()
            try:
                cur.execute("DROP DATABASE test")
                conn.commit()
            except mariadb.Error as e:
                print("Database test does not exist! Continuing on anyway...")
                
            cur.execute("CREATE DATABASE test")
            self.create_table("players", data)
            columns = ["id", "event", "uuid", "discordID", "message"]
            values = ["1", "create", "uuid goes here", "discord ID goes here", "debug ticket"]
            self.insert("players", columns, values)
            conn.commit()
        except mariadb.Error as e:
            print(f"Database error in reset_to_default statement: {e}")
        finally:
            if conn:
                conn.close()

    #DANGEROUS FUNCTION!!!
    #WILL BE DEPRECIATED LATER
    #This function exists PURELY for testing raw SQL lines, DO NOT USE IT WITH USER INPUT!!!!
    def execute(self, command, variables=None):
        conn = self.create_connection()
        cur = conn.cursor()
        if variables:
            cur.execute(command, variables)
        else:
            cur.execute(command)
        conn.commit()
        conn.close()

    #Takes in a list of columns and a table, returns all information from the select statement.
    #where_conditions should be formatted as a dictionary.
    #For example, if you're selecting from the column of player names where name = "notch";
    #where_conditions = {"name" : "Notch"}

    #Doesn't support OR statements yet
    def select(self, columns:list, table:str, where_conditions=None,):

        #First remove everything except letters/numbers (and the all character) from column names
        safe_columns = []
        safe_columns_string = ""
        index = 0
        for column in columns:
            sanitized = re.sub(r"[^0-9A-Za-z*]", "", column)
            safe_columns.append(sanitized)
            if index < len(columns)-1:
                safe_columns_string = safe_columns_string + sanitized + ", "
            else:
                safe_columns_string = safe_columns_string + sanitized

            index += 1

        #Make sure the table variable is safe too
        safe_table = re.sub(r"[^0-9A-Za-z*]", "", table)

        sql = f"SELECT {safe_columns_string} FROM {safe_table}"
        
        if where_conditions:
            #Gotta sanitize the conditions too
            safe_keys = []
            for key in where_conditions.keys():
                safe_key = re.sub(r"[^0-9A-Za-z]", "", key)
                safe_keys.append(safe_key)


            sql += f" WHERE {safe_keys[0]}=?"
            #TODO:
            #Implement OR statements
            if len(safe_keys) > 1:
                for key in safe_keys[1:]:
                    sql += f" AND {key}=?"
            #and the paramaters
            safe_values = []
            for value in where_conditions.values():
                safe_value = re.sub(r"[^0-9A-Za-z ]", "", value)
                safe_values.append(safe_value)

            params = safe_values
        results = None
        try:
            #Create a connection, fetch the cursor/data, close the connection and return results
            conn = self.create_connection()
            cur = conn.cursor()

            #DEBUGGING
            #print(f"\n{sql}\n")
            #If no conditions, ignore the parameters
            if where_conditions:
                cur.execute(sql, params)
            else:
                cur.execute(sql)

            results = cur.fetchall()
        except mariadb.Error as e:
            print(f"Database error in select statement: {e}")
        finally:
            if conn:
                conn.close()
        return results


    #Runs an INSERT INTO SQL command
    #Structured as follows:
    #INSERT INTO {table} (column1, column2, column(n)) VALUES (value1, value2, value(n))
    
    #TODO: Refactor columns and values to be a dictionary instead of 2 separate lists
    def insert(self, table:str, columns:list, values:list):
        #Sanitize, sanitize, sanitize

        safe_table = re.sub(r"[^0-9A-Za-z]", "", table)
        
        safe_columns = []
        for column in columns:
            safe_columns.append(re.sub(r"[^0-9A-Za-z]", "", column))

        safe_values = []
        for value in values:
            safe_values.append(re.sub(r"[^0-9A-Za-z ]", "", str(value)))

        columns_string = "("
        index = 0
        for column in safe_columns:
            if index < len(safe_columns)-1:
                columns_string += f"{column}, "
            else:
                columns_string += f"{column})"
            index += 1

        q_marks = "?, " * (len(safe_columns)-1)
        inputs = "(" + q_marks + "?)"
        sql = f"INSERT INTO {safe_table} {columns_string} VALUES {inputs}"
        #DEBUGGING
        #print(f"INSERT SQL: \n{sql}\n VALUES: {safe_values}\n")
        params = safe_values
        try:
           #Create a connection, insert the data, close the connection.
           conn = self.create_connection()
           cur = conn.cursor()
           cur.execute(sql, params)
           conn.commit()
        except mariadb.Error as e:
            print(f"Database error in insert statement: {e}")
        finally:
            if conn:
                conn.close()

    #Makes an SQL table.
    #Table Data is an array of string tuples, with the first value being the column name, and the second value being the data it holds.
    def create_table(self, table:str, table_data:list):
        #Sanitize like it's mid 2020
        safe_table = re.sub(r"[^0-9A-Za-z]", "", table)

        safe_table_data = []
        for data in table_data:
            regex = r"[^0-9A-Za-z()]"
            temp_tuple = (re.sub(regex, "", data[0]), re.sub(regex, "", data[1]))
            safe_table_data.append(temp_tuple)
        
        table_data_string = "("
        index = 0
        for column in safe_table_data:
            if index < len(safe_table_data)-1:
                table_data_string += f"{column[0]} {column[1]}, "
            else:
                table_data_string += f"{column[0]} {column[1]});"

            index += 1

        #Example output:
        #CREATE TABLE players (Name varchar(255), IngameID int, ticketID int)
        sql = f"CREATE TABLE {safe_table} {table_data_string}"
        #DEBUGGING
        #print(f"\n{sql}\n")
        try:
           #Create a connection, insert the data, close the connection.
           conn = self.create_connection()
           cur = conn.cursor()
           cur.execute(sql)
           conn.commit()
        except mariadb.Error as e:
            print(f"Database error in create_table statement: {e}")
        finally:
            if conn:
                conn.close()
    
    #Drops a table
    #This is likely to be removed once the project is deployed, since we dont want old info being deleted.
    def drop_table(self, table:str):
        #yes, I'm sanitizing in the drop table function.
        safe_table = re.sub(r"[^0-9A-Za-z]", "", table)
        sql = f"DROP TABLE {safe_table}"
        try:
            #Create a connection, insert the data, close the connection.
            conn = self.create_connection()
            cur = conn.cursor()
            cur.execute(sql)
            conn.commit()
        except mariadb.Error as e:
            print(f"Database error in drop_table statement: {e}")
        finally:
            if conn:
                conn.close()

    def delete_row(self, table:str, variable:str, value:str, type:str):
        #You know the drill
        safe_table = re.sub(r"[^0-9A-Za-z]", "", table)
        safe_variable = re.sub(r"[^0-9A-Za-z]", "", variable)
        safe_value = re.sub(r"[^0-9A-Za-z]", "", value)

        if type == "int":
            safe_value = f"{safe_value}"
        else:
            safe_value = f"'{safe_value}'"


        sql = f"DELETE FROM {safe_table} WHERE {safe_variable}='{safe_value}'"
        try:
           #Create a connection, insert the data, close the connection.
           conn = self.create_connection()
           cur = conn.cursor()
           cur.execute(sql)
           conn.commit()
        except mariadb.Error as e:
            print(f"Database error in update_row statement: {e}")
        finally:
            if conn:
                conn.close()

        

    def update_row(self, table:str, variables:list, values:list, id:int):
        #Untested, might behave strangely
        #Assumes table uses IDs as primary key

        if len(variables) != len(values):
            raise Exception(f"Error in updating SQL row: Variables and Values contain different numbers of input.\nVariables:{variables}\nValues:{values}")

        safe_table = re.sub(r"[^0-9A-Za-z]", "", table)
        safe_variables = []
        for item in variables:
            safe_variables.append(re.sub(r"[^0-9A-Za-z]", "", item))
        
        safe_values = []
        for item in values:
            safe_values.append(re.sub(r"[^0-9A-Za-z]", "", item))

        sql = f"UPDATE {safe_table} SET"
        for i in range(0,len(safe_values)-1):
            sql += f" {safe_variables[i]} = '{safe_values[1]}'"
            if i < (len(safe_values)-1):
                sql += ","
        sql += f"WHERE id = {id};"

        try:
           #Create a connection, insert the data, close the connection.
           conn = self.create_connection()
           cur = conn.cursor()
           cur.execute(sql)
           conn.commit()
        except mariadb.Error as e:
            print(f"Database error in update_row statement: {e}")
        finally:
            if conn:
                conn.close()

    #Fetches the entry with the highest ID, presumably the most recently entered ticket
    #Returns a list containing each item in the row
    def get_most_recent_entry(self, table:str) -> list:
        safe_table = re.sub(r"[^0-9A-Za-z]", "", table)

        sql = f"SELECT * FROM {safe_table} ORDER BY id DESC LIMIT 1"
        try:
            #Create a connection, insert the data, close the connection.
            conn = self.create_connection()
            cur = conn.cursor()
            cur.execute(sql)
            result = cur.fetchall()
            conn.commit()
        except mariadb.Error as e:
            print(f"Database error in get_most_recent_entry statement: {e}")
        finally:
            if conn:
                conn.close()

        return result[0]

#Only runs when this py file is run by itself
#This is basically just my debugging
if __name__ == "__main__":
    s = SQLManager()
    s.drop_table("players")                                                                # May change to int?
    data = [("id", "int"), ("event", "varchar(255)"), ("uuid", "varchar(255)"), ("discordID", "varchar(255)"), ("message", "varchar(255)")]
    s.create_table("players", data)

    columns = ["id", "event", "uuid", "discordID", "message"]
    values = ["1", "create", "uuid goes here", "discord ID goes here", "debug ticket"]
    
    s.insert("players", columns, values)
    print(s.select("*", "players"))
