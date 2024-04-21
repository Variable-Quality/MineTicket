from sql import SQLManager
from os import path
from configmanager import database_config_manager as db_cfm
import mariadb
import discord.utils


STAFF_ROLE = "Staff"

# Helper class for containerizing players
class Player:

    def __init__(self, name: str, discord_id: str, is_staff: bool = False):
        self.name = name
        self.discord_id = discord_id
        self.staff = is_staff

    def __str__(self):
        return f"{self.name},{self.discord_id},{str(self.staff)}"
    
    def __int__(self):
        return int(self.discord_id)

##### Delete: Remove commmentttt - aRt #####
# Table object
# Not too useful now, maybe make the primary way of interacting with tables?
##### Delete END #####
class Table:

    def __init__(self, config:str=None):
        cfm = db_cfm(filename=config)
        self.name = cfm.cfg["DATABASE"]["table"]

        self.columns = list(cfm.cfg["TABLE"].keys())

        datatypes_list = []
        for key in self.columns:
            datatypes_list.append(cfm.cfg["TABLE"][key])
        self.datatypes = datatypes_list

    # Pushes table to DB.
    # Only used when the table is not yet in the DB
    def push(self):
        manager = SQLManager()
        data = {}
        for i in range(0, len(self.columns) - 1):
            data[self.columns[i]] = self.datatypes[i]

        manager.create_table(self.name, data)


class TableEntry:
    ##### Delete: todo - Art #####
    # TODO: Dynamic Column names, maybe add origin server?
    ##### Delete END #####

    # Data handler class for a ticket. Contains everything a ticket should.
    # Leave ID as none if the ticket is not in the DB yet.
    def __init__(
        self,
        table_info:dict=None,
        config:str=None,
    ):
        self._manager = SQLManager()
        self.cfm = db_cfm(filename=config)
        if not table_info:
            self.table_dict = self.cfm.cfg["TABLE"]

        else:
            self.table_dict = table_info

        for key in self.table_dict.keys():
            self.__dict__[key] = self.table_dict[key]

        self.columns = list(self.table_dict.keys())[1:]
    ##### Delete: i see - Art #####
    # Janky workaround to update dict items to match class attributes
    # Could move this to the update() function, or push(), or both
    ##### Delete END #####
    def update_dict(self):
        for key in self.table_dict.keys():
            self.table_dict[key] = self.__dict__[key]


    def __str__(self):
        ret_str = ""
        for key in self.table_dict.keys():
            ret_str += f"{key}: {self.table_dict[key]}\n"
        return ret_str

    # Returns a more readable  string
    # This method uses some hardcoded database columns, I can't figure out a smart way around that
    def to_str(self):
        pdata_discord = self.table_dict["involved_players_discord"]
        if len(pdata_discord) > 0:
            names = []
            players = pdata_discord.split("|")
            for player in players:
                names.append(player.split(',')[0])
        try:
            sname = self.involved_staff_discord.split(",")[1]
        except IndexError:
            sname = ""
        return f"Ticket ID: {self.table_dict['id']}\nPlayers: [{players}]\nStaff: [{sname}]\nMessage: {self.table_dict['message']}\nStatus: {self.table_dict['status']}"

    # Adds the Table into the database table specified in the init
    def push(self):
        # If the entry exists with that ID, warn and return.
        try:
            table_entry = fetch_by_id(int(self.table_dict["id"]))
        except TypeError:
            table_entry = None
        if table_entry != None:
            print(
                f"WARNING!!! Ticket with ID {self.table_dict['id']} (likely) already exists! Use update() instead!"
            )
            return

        values = []
        for key in self.table_dict.keys():
            values.append(self.table_dict[key])
        #Ignore the ID 
        values = values[1:]
        try:
            self._manager.insert(self.cfm.cfg["DATABASE"]["table"], self.columns, values)
        except mariadb.Error as e:
            print(f"Error pushing ticket with ID {self.id} \n{e}")

    # Updates an existing ticket in the database with the current TableEntry object.
    def update(self):
        # These values are in order depending on the SQL database columns
        values = []
        for key in list(self.table_dict.keys())[1:]:
            values.append(self.table_dict[key])
        self._manager.update_row(self.cfm.cfg["DATABASE"]["table"], self.columns, values, self.id)
##### Delete: remove todo #####
# Quick and dirty table manager for the JSON parsing
# Makes sure we clean up any messages created by/closed by the JSON
# TODO:
# Periodic check to ensure messages have not been otherwise handled
# Create this table alongside everything else
##### Delete END #####
class json_table_manager:

    def __init__(self, table_exists=True):
        self._manager = SQLManager()
        self.data = {"id": "PRIMARY KEY",
                     "message_ids": "TEXT"}
        if not table_exists:
            self._manager.create_table("json_messages", self.data, is_serial=False)

    def add_message(self, message:discord.Message, id:int):
        self._manager.insert(table="json_messages", columns=list(self.data.keys()), values=[id, message.id])

    def remove_message(self, message_id:int):
        self._manager.delete_row(table="json_messages", variable="id", value=message_id, type="int")
    

# Allows access to the SQLManager reset_to_default command
def reset_to_default(debug_entry=False, config:str=None):
    manager = SQLManager()
    manager.reset_to_default(debug_entry, config)


def fetch_by_id(id: int, config:str=None) -> TableEntry:
    cfm = db_cfm(filename=config)
    table = cfm.cfg["DATABASE"]["table"]
    columns = list(cfm.cfg["TABLE"].keys())
    manager = SQLManager()

    
    try:
        res = manager.select(columns, table, {"id": f"{str(id)}"})[0]
        # print(result)
    except IndexError:
        return None
    
    table_dict = {}
    index = 0
    for column in columns:
        table_dict[column] = res[index]
        index += 1

    return TableEntry(table_info=table_dict)


# Fetches all tickets with a certain status (open, closed)
# By default will return TableEntry objects of all entries found, otherwise itll go to the cap specified by max
def fetch_by_status(status: str, cfg:str=None, max: int = 0) -> list:
    manager = SQLManager()
    cfm = db_cfm(filename=cfg)
    table = cfm.cfg["DATABASE"]["table"]
    columns = list(cfm.cfg["TABLE"].keys())

    result = manager.select(columns, table, {"status": status})
    if max > 0:
        result = result[:max]

    entries = []
    for res in result:
        table_dict = {}
        index = 0
        for column in columns:
            table_dict[column] = res[index]
            index += 1
        # print(result)
        temp = TableEntry(
            table_info=table_dict
        )
        entries.append(temp)

    return entries

##### Delete: todo #####
# Allows access to the function in sql.py of the same name
# TODO:
# Pull entry into a TableEntry object rather than just a list
##### Delete END #####
def get_most_recent_entry(table, only_id=False):
    manager = SQLManager()
    entry = manager.get_most_recent_entry(table, only_id)
    return entry


# Returns a player object given an interaction
##### Delete: maybe - Art #####
# Maybe move this function to a different file? Feels out of place
##### Delete END #####
def player_from_interaction(interaction: discord.Interaction) -> Player:
    author = interaction.user
    staff = False
    staff_role = discord.utils.find(
        lambda r: r.name == STAFF_ROLE, interaction.guild.roles
    )
    if staff_role in author.roles:
        staff = True

    return Player(author.name, str(author.id), staff)

if __name__ == "__main__":
    t = TableEntry()
    reset_to_default(debug_entry=True)
    print(t.table_dict)
    print(fetch_by_id(1))
    dict = {"id": 2, 
            "involved_players_discord": "9871623089476", 
            "involved_players_minecraft": "sdd987f9a879-9-3218h494",
            "involved_staff_discord": "973424576456",
            "involved_staff_minecraft": "asiudas98sdf98-238urw9efh98-asd97f80",
            "status": "open",
            "message": "big joey slapnuts"}
    te = TableEntry(table_info=dict)
    te.push()
    print(fetch_by_id(2))
    print(te.table_dict)
