from sql import SQLManager
from os import path
from configmanager import database_config_manager as db_cfg
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


# Table object
# Not too useful now, maybe make the primary way of interacting with tables?
class Table:

    def __init__(self, config:str=None):
        cfg = db_cfg(filename=config)
        cfg.read(config)
        self.name = cfg["DATABASE"]["table"]

        self.columns = list(cfg["TABLE"].keys())

        datatypes_list = []
        for key in self.columns:
            datatypes_list.append(cfg["TABLE"][key])
        self.datatypes = datatypes_list

    # Pushes table to DB.
    # Only used when the table is not yet in the DB
    def push(self):
        manager = SQLManager()
        data = []
        for i in range(0, len(self.columns) - 1):
            data.append((self.columns[i], self.datatypes[i]))

        manager.create_table(self.name, data)


# Global variable containing all column names
# TODO: Get from SQL command directly (or cfg)
columns = ["involved_players", "involved_staff", "message", "status"]


class TableEntry:
    # TODO: Dynamic Column names, maybe add origin server?

    # Data handler class for a ticket. Contains everything a ticket should.
    # Leave ID as none if the ticket is not in the DB yet.
    def __init__(
        self,
        table_info:dict=None,
        config:str=None,
    ):
        self._manager = SQLManager()
        if not table_info and not config:
            raise Exception("ERROR: TableEntry must contain either a dict or config file with information on the database table.")
        if not table_info:
            cfg = db_cfg(config)
            self.table_dict = dict(cfg["TABLE"])
        else:
            self.table_dict = dict(table_info)


    def __str__(self):
        ret_str = ""
        for key in self.table_dict.keys():
            ret_str += f"{key}: {self.table_dict[key]}\n"
        return ret_str

    # Returns a more readable  string
    # This method uses some hardcoded database columns, I can't figure out a smart way around that
    def to_str(self):
        pdata_discord = self.cfg["TABLE"]["involved_players_discord"]
        if len(pdata_discord) > 0:
            names = []
            players = pdata_discord.split("|")
            for player in players:
                names.append(player.split(',')[0])
        pname = self.cfg[""].split(",")[1]
        try:
            sname = self.involved_staff.split(",")[1]
        except IndexError:
            sname = ""
        return f"Ticket ID: {str(self.id)}\nPlayers: [{pname}]\nStaff: [{sname}]\nMessage: {self.message}\nStatus: {self.status}"

    # Adds the Table into the database table specified in the init
    def push(self):
        # If we gave the entry an ID, disable push.
        if not self.id == None:
            print(
                f"WARNING!!! Ticket with ID {self.id} (likely) already exists! Use update() instead!"
            )
            return

        values = [self.involved_players, self.involved_staff, self.message, self.status]
        try:
            self._manager.insert(self.table, columns, values)
        except mariadb.Error as e:
            print(f"Error pushing ticket with ID {self.id} \n{e}")

    # Updates an existing ticket in the database with the current TableEntry object.
    def update(self):
        # These values are in order depending on the SQL database columns
        values = [self.involved_players, self.involved_staff, self.message, self.status]
        self._manager.update_row(self.table, columns, values, self.id)


# Allows access to the SQLManager reset_to_default command
def reset_to_default():
    manager = SQLManager()
    manager.reset_to_default()


def fetch_by_id(id: int, table: str) -> TableEntry:
    manager = SQLManager()
    result = manager.select(columns, table, {"id": f"{str(id)}"})[0]
    try:
        table_entry = TableEntry(
            players=result[0],
            staff=result[1],
            message=result[2],
            status=result[3],
            table=table,
            id=id,
        )
    except IndexError:
        return None

    return table_entry


# Fetches all tickets with a certain status (open, closed)
# By default will return TableEntry objects of all entries found, otherwise itll go to the cap specified by max
def fetch_by_status(status: str, cfg:str=None, max: int = 0) -> list:
    manager = SQLManager()
    config = db_cfg(filename=cfg)
    cols = list(config["TABLE"].keys())
    result = manager.select(cols, config["DATABASE"]["table"], {"status": status})
    if max > 0:
        result = result[:max]

    entries = []
    for res in result:
        print(result)
        temp = TableEntry(
            id=res[0],
            players=res[1],
            staff=res[2],
            message=res[3],
            status=status,
            table=table,
        )
        entries.append(temp)

    return entries


# Allows access to the function in sql.py of the same name
def get_most_recent_entry(table, only_id=False):
    manager = SQLManager()
    entry = manager.get_most_recent_entry(table, only_id)
    return entry


# Returns a player object given an interaction
# Maybe move this function to a different file? Feels out of place
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
    # m = SQLManager()
    # m.reset_to_default(debug_entry=True)
    # build_cfg("players", (("event", "varchar(255)"), ("involved_players", "varchar(255)"), ("involved_staff", "varchar(255)"), ("message", "varchar(255)"), ("status", "varchar(255)")))
    # d = Table("players.ini")
    # d.push()
    # t = TableEntry("ya mama", "howbowda", "shabo'opadoo\\", "status", "players")
    # t.push()
    # print(fetch_by_id(2, "players"), "\n")
    # t = TableEntry("Updated ticket", "iushdiug", "godless program this is", "open","players", 2)
    # t.update()
    # print(fetch_by_id(2, "players"))
    print(str(fetch_by_status("open", "players")[0]))
