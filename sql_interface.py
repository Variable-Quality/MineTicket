from sql import SQLManager
from os import path
from configparser import ConfigParser
import mariadb

#TODO:
#Create function that adds example entry for testing

#Creates a config file for interfacing with a Database
#columns list should be a list of tuples, with the first item being the column name
#Second tuple item being its datatype
#Ex: columns=[("id", "int"), ("name", "varchar(255)")]
def build_cfg(name:str, columns:list):
    config = ConfigParser()
    config["TABLE"] = {"name" : name}
    columns_str = ""
    datatypes_str = ""
    for column in columns:
        
        columns_str += f"{column[0]},"
        datatypes_str += f"{column[1]},"

    config["TABLE"]["columns"] = columns_str[:len(columns_str)-1]
    config["TABLE"]["datatypes"] = datatypes_str[:len(datatypes_str)-1]

    filename = f"{name}.ini"
    if path.isfile(filename):
        with open(filename, "w") as f:
            config.write(f)
    else:
        with open(filename, "x") as f:
            config.write(f)



class Table():

    def __init__(self, config:str):
        cfg = ConfigParser()
        cfg.read(config)
        self.name = cfg["TABLE"]["name"]

        columns_list = cfg["TABLE"]["columns"].split(",")
        self.columns = columns_list

        datatypes_list = cfg["TABLE"]["datatypes"].split(",")
        self.datatypes = datatypes_list

    #Pushes table to DB.
    def push(self):
        manager = SQLManager()
        data = []
        for i in range(0, len(self.columns)-1):
            data.append((self.columns[i], self.datatypes[i]))

        manager.create_table(self.name, data)


#Global variable containing all column names
#TODO: Get from SQL command directly
columns = ["id", "involved_players", "involved_staff", "message"]

class TableEntry():
    #TODO: Dynamic Column names

    #Data handler class for a ticket. Contains everything a ticket should, and can automatically assign a new ticket ID if none is given.
    #Unless the table entry already exists in the DB, DO NOT ASSIGN IT AN ID!
    #When the table entry is pushed the system will give it a new ID.
    def __init__(self, players:str, staff:str, message:str, table:str, id:int = -1):
        self._manager = SQLManager()

        self.involved_players = players
        self.involved_staff = staff
        self.message = message
        self.table = table
        self.id = id

    #Adds the Table into the database table specified in the init
    def push(self):
        #If we haven't given the entry an ID, query the server and give it the next available ID
        if self.id == -1:
            try:
                self.id = int(self._manager.get_most_recent_entry(self.table)[0])+1
            #If theres nothing in the database yet, just give it an ID of 1.
            #Should never happen, but yknow.
            except IndexError:
                self.id = 1
        else:
            print(f"WARNING!!! Ticket with ID {self.id} already exists! Use update() instead!")
            return
        values = [str(self.id), self.involved_players, self.involved_staff, self.message]
        try:
            self._manager.insert(self.table, columns, values)
        except mariadb.Error as e:
            print(f"Error pushing ticket with ID {self.id} \n{e}")

    #Updates an existing ticket in the database with the current TableEntry object.
    def update(self):
        values = [str(self.id), self.involved_players, self.involved_staff, self.message]
        self._manager.update_row(self.table, columns, values, self.id)



#Allows access to the SQLManager reset_to_default command
def reset_to_default():
    manager = SQLManager()
    manager.reset_to_default()

def fetch_by_id(id:int, table:str) -> TableEntry:
    manager = SQLManager()
    result = manager.select(columns, table, {"id" : f"{str(id)}"})[0]
    table_entry = TableEntry(players=result[1], staff=result[2], message=result[3], table=table, id=id)

    return table_entry

if __name__ == "__main__":
    m = SQLManager()
    m.reset_to_default()
    build_cfg("players", (("id", "int"), ("event", "varchar(255)"), ("involved_players", "varchar(255)"), ("involved_staff", "varchar(255)"), ("message", "varchar(255)")))
    d = Table("players.ini")
    d.push()
    t = TableEntry("ya mama", "howbowda", "shaboopadoo", "players")
    t.push()
    t = TableEntry("Updated ticket", "iushdiug", "god hell fuck", "players", 2)
    t.update()
    print(fetch_by_id(2, "players"))
