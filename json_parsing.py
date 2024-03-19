import json
import sql_interface as sql

class message():

    def __init__(self, message):
        json_format = json.loads(message.content)
        self.message_object = message
        self.event = json_format["event"]
        self.player_id = json_format["discord-id"]
        #Not sure what to do with this atm but I would imagine its something ingame
        #So for now it has a place in the message object
        self.player_uuid = json_format["player-uuid"]
        self.id = int(json_format["id"])
        self.message = json_format["message"]

        self.active_entry = sql.fetch_by_id(self.id)