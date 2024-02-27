from sql import SQLManager
from os import path
from configparser import ConfigParser
import mariadb

#TODO:
#Create function that adds example entry for testing

#Creates a config file for interfacing with a Database
#columns list should be tuples of strings
#First item in the tuple is the column name, second item is the datatype
def build_cfg(name:str, columns:list):
    config = ConfigParser()
    config["TABLE"] = {"name" : name}
    columns_str = ""
    datatypes_str = ""
    config["TABLE"]["columns"] = []
    config["TABLE"]["datatypes"] = []
    for column in columns:
        columns_str += f"{column[0]},"
        datatypes_str += f"{columns[1]},"

    columns_str = columns_str[:len(columns_str)-1]
    datatypes_str = datatypes_str[:len(datatypes_str)-1]
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


#Global variable containing all column names
#TODO: Get from SQL command directly
columns = ["id", "event", "uuid", "discordID", "message"]

class TableEntry():


    #TODO: Dynamic Column names

    #Data handler class for a ticket. Contains everything a ticket should, and can automatically assign a new ticket ID if none is given.
    def __init__(self, event:str, uuid:str, discordID:str, message:str, table:str, id:int = -1):
        self._manager = SQLManager()
        valid_events = ["create", "claim", "close"]
        if event not in valid_events:
            raise Exception(f"Invalid event given to sql_interface: {event}, expected {valid_events}")
        
        if id == -1:
            #RACE CONDITION!!!!!!
            id = int(self._manager.get_most_recent_entry(table)[0]) + 1

        self.event = event
        self.uuid = uuid
        self.discordID = discordID
        self.message = message
        self.table = table
        self.id = id

    #Adds the Table into the database table specified in the init
    def push(self):
        values = [str(self.id), self.event, self.uuid, self.discordID, self.message]
        try:
            self._manager.insert(self.table, columns, values)
        except mariadb.Error as e:
            print(f"Error pushing ticket with ID {self.id} \n{e}")



#Allows access to the SQLManager reset_to_default command
def reset_to_default():
    manager = SQLManager()
    manager.reset_to_default()

def fetch_by_id(id:int, table:str):
    manager = SQLManager()
    result = manager.select(columns, table, {"id" : f"{str(id)}"})
    return result[0]

if __name__ == "__main__":
    build_cfg("main", {"players" : ["id", "name", "uuid"]})
    d = Database("main.ini")
    print(d.values)