from sql import SQLManager
from os import path
from configparser import ConfigParser
import mariadb
import discord.utils

#TODO:
#Create function that adds example entry for testing



STAFF_ROLE = "Staff"

#Creates a config file for interfacing with a Database
#columns list should be a list of tuples, with the first item being the column name
#Second tuple item being its datatype
#Ex: columns=[("name", "varchar(255)"), ("playerid", "bigint")]
#Note: Program assumes the first column is the ID column, and sets it as the primary key automatically
#So don't worry about including that
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

#Helper class for containerizing players
class Player():

    def __init__(self, name:str, discord_id:str, is_staff:bool=False):
        self.name = name
        self.discord_id = discord_id
        self.staff = is_staff

    def __str__(self):
        return f"{self.name},{self.discord_id},{str(self.staff)}"
    

#Table object
#Not too useful now, maybe make the primary way of interacting with tables?
#Ask everyone else
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
    #Only used when the table is not yet in the DB
    def push(self):
        manager = SQLManager()
        data = []
        for i in range(0, len(self.columns)-1):
            data.append((self.columns[i], self.datatypes[i]))

        manager.create_table(self.name, data)


#Global variable containing all column names
#TODO: Get from SQL command directly (or cfg)
columns = ["involved_players", "involved_staff", "message", "status"]

class TableEntry():
    #TODO: Dynamic Column names, maybe add origin server?

    #Data handler class for a ticket. Contains everything a ticket should.
    #Leave ID as none if the ticket is not in the DB yet.
    def __init__(self, players:str, staff:str, message:str, status:str, table:str, id:int=None):
        self._manager = SQLManager()

        self.id = id
        self.involved_players = players
        self.involved_staff = staff
        self.message = message
        self.table = table
        self.status = status
        

    def __str__(self):
        return f"Ticket ID: {str(self.id)}\nPlayers: [{self.involved_players}]\nStaff: [{self.involved_staff}]\nMessage: {self.message}\nStatus: {self.status}"

    #Adds the Table into the database table specified in the init
    def push(self):
        #If we gave the entry an ID, disable push.
        if not self.id == None:
            print(f"WARNING!!! Ticket with ID {self.id} (likely) already exists! Use update() instead!")
            return
        
        values = [self.involved_players, self.involved_staff, self.message, self.status]
        try:
            self._manager.insert(self.table, columns, values)
        except mariadb.Error as e:
            print(f"Error pushing ticket with ID {self.id} \n{e}")

    #Updates an existing ticket in the database with the current TableEntry object.
    def update(self):
        #These values are in order depending on the SQL database columns
        values = [self.involved_players, self.involved_staff, self.message, self.status]
        self._manager.update_row(self.table, columns, values, self.id)



#Allows access to the SQLManager reset_to_default command
def reset_to_default():
    manager = SQLManager()
    manager.reset_to_default()

def fetch_by_id(id:int, table:str) -> TableEntry:
    manager = SQLManager()
    result = manager.select(columns, table, {"id" : f"{str(id)}"})[0]
    table_entry = TableEntry(players=result[0], staff=result[1], message=result[2], status=result[3], table=table, id=id)

    return table_entry

#Fetches all tickets with a certain status (open, closed)
#By default will return TableEntry objects of all entries found, otherwise itll go to the cap specified by max
def fetch_by_status(status:str, table:str, max:int=0):
    manager = SQLManager()
    #Janky way of including column ID here
    #I only did this because the initial DB adds id as a column whether or not its in the list
    #Ain't stupid if it works and doesn't affect performance too bad I guess
    cols = list(columns)
    cols.insert(0, "id")
    print(cols)
    result = manager.select(cols, table, {"status" : status})
    if max > 0:
        result = result[:max]

    entries = []
    for res in result:
        print(result)
        temp = TableEntry(id=res[0], players=res[1], staff=res[2], message=res[3], status=status, table=table)
        entries.append(temp)

    return entries

#Allows access to the function in sql.py of the same name
def get_most_recent_entry(table, only_id=False):
    manager = SQLManager()
    entry = manager.get_most_recent_entry(table, only_id)
    return entry


#Returns a player object given an interaction
#Maybe move this function to a different file? Feels out of place
def player_from_interaction(interaction:discord.Interaction) -> Player:
    try:
        author = interaction.message.author
    except AttributeError:
        #Some interactions have a message, others dont (I think)
        #TODO: review this
        author = interaction.user

    staff = False
    staff_role = discord.utils.find(lambda r: r.name == STAFF_ROLE, interaction.guild.roles)
    if staff_role in author.roles:
        staff = True

    return Player(author.name, str(author.id), staff)

if __name__ == "__main__":
    #m = SQLManager()
    #m.reset_to_default(debug_entry=True)
    #build_cfg("players", (("event", "varchar(255)"), ("involved_players", "varchar(255)"), ("involved_staff", "varchar(255)"), ("message", "varchar(255)"), ("status", "varchar(255)")))
    #d = Table("players.ini")
    #d.push()
    #t = TableEntry("ya mama", "howbowda", "shabo'opadoo\\", "status", "players")
    #t.push()
    #print(fetch_by_id(2, "players"), "\n")
    #t = TableEntry("Updated ticket", "iushdiug", "godless program this is", "open","players", 2)
    #t.update()
    #print(fetch_by_id(2, "players"))
    print(str(fetch_by_status("open", "players")[0]))
