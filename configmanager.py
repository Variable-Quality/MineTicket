from configparser import ConfigParser
import os.path

#path to config directory
CONFIG_LOCATION = "config"

#Really basic config file manager, mostly made it to have it
#Not sure if it'll be useful
class config_manager():

    def __init__(self, filename:str):
        self.filename = filename
        self.cfg = ConfigParser()

        #If the file already exists, read it into the configparser
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                self.cfg.read(f)

    def change_file(self, filename:str):
        self.filename = filename

    #Overwrites current file with dictionary passed in
    def write_file(self, data:dict):
        with open(self.filename, "w") as f:
            self.cfg = data
            self.cfg.write(f)

class database_config_manager():

    # If creating a new config, pass in a dict to data, and information such as database name, table name, and login info into the info dict.
    # Skip the ID field, that one is assumed.
    # Ex: data={"involved_player_discord": "varchar(255)", "involved_player_minecraft": "varchar(255)", ...}
    # Ex: info = {"database": "test", "table": "tickets", "username": "root", "password": "toor", ...}
    #
    # If loading existing config, pass in the filename (extension included)
    # Note: This code assumes a single table. It could be modified to expect multiple, however we don't believe it's needed in this application.
    def __init__(self, data:dict=None, info:dict=None, filename:str=None):
        self.cfg = ConfigParser()
        self.filename = f"{CONFIG_LOCATION}/{filename}"
        if (data and not info) or (info and not data):
            raise Exception("WARNING!! Config file MUST contain both the data and information of the database!!")
        
        elif data and info:
            data["id"] = "SERIAL PRIMARY KEY"
            self.cfg["DATABASE"] = info
            self.cfg["TABLE"] = data
            self.filename = f"{CONFIG_LOCATION}/{info['database']}.ini"

        elif filename:
            with open(self.filename, "r") as f:
                self.cfg.read(self.filename)

        # If all 3 are none, use the premade config file.       
        else:
            self.default_config()

    def default_config(self):
        # Table name is stored in the DATABASE section since its much easier to use the keys of the TABLE section to define column names
        self.cfg["DATABASE"] = {"database": "test", 
                                "table": "tickets", 
                                "username": "root", 
                                "password": "toor",
                                "host": "localhost",
                                "port": "3306"}
        
        self.cfg["TABLE"] = {"id": "SERIAL PRIMARY KEY",
                              #involved_players is a TEXT object just in case there are a metric ton of players on one ticket
                              "involved_players_discord": "TEXT",
                              "involved_players_minecraft": "TEXT",
                              "involved_staff_discord": "varchar(256)",
                              "involved_staff_minecraft": "varchar(256)",
                              "status": "varchar(16)",
                              "message": "TEXT"}
        
        self.filename = f"{CONFIG_LOCATION}/default.ini"

    def write(self):
        if os.path.isfile(self.filename):
            writemode = "w"
        else:
            writemode = "x"

        with open(f"{self.filename}", writemode) as f:
            self.cfg.write(f)

    def read(self, filename:str=None):
        if filename:
            self.filename = filename
        with open(self.filename, "r") as f:
            self.cfg.read(f)




