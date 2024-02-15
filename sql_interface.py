from sql import SQLManager
import mariadb

manager = SQLManager()

#Global variable containing all column names
#TODO: Get from SQL command directly
columns = ["id", "event", "uuid", "discordID", "message"]

class TableEntry():


    #TODO: Dynamic Column names

    #Data handler class for a ticket. Contains everything a ticket should, and can automatically assign a new ticket ID if none is given.
    def __init__(self, event:str, uuid:str, discordID:str, message:str, table:str, id:int = -1):
        valid_events = ["create", "claim", "close"]
        if event not in valid_events:
            raise Exception(f"Invalid event given to sql_interface: {event}, expected {valid_events}")
        
        if id == -1:
            #RACE CONDITION!!!!!!
            id = int(manager.get_most_recent_entry(table)[0]) + 1

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
            manager.insert(self.table, columns, values)
        except mariadb.Error as e:
            print(f"Error pushing ticket with ID {self.id} \n{e}")

def fetch_by_id(id:int, table:str):
    result = manager.select(columns, table, {"id" : f"{str(id)}"})
    return result

if __name__ == "__main__":
    t = TableEntry("create", "uuid", "discordID", "message", "players")
    t2 = TableEntry("create", "uuid", "discordID", "message", "players")
    t2.push()
    entry = fetch_by_id(1, "players")
    entry2 = fetch_by_id(2, "players")
    print(entry)
    print(entry2)