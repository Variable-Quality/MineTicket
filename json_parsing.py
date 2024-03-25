import discord
import json
import sql_interface as sql

# lets assume that a channel called #intake,
# in the category called "Tickets" will be made,
# make sure JSONParser only reads from there

class ParseJSON():
    def __init__(self, guild):
        self.guild = guild

    async def check_json_messages(self, client):
        category_name = "Tickets"
        channel_name = "intake"

        #check if setup was performed
        category = discord.utils.get(self.guild.categories, name = category_name)
        if not category:
            print(f"Category '{category_name}' not found in guild '{self.guild.name}")
            return
        channel = discord.utils.get(category.text_channels, name = channel_name)
        if not channel:
            print(f"Channel '{channel_name}' not found in category '{category_name}'")
            return
        # wait i got tired here what am i doing
        # help

    # ok time to read JSON
    async def parse_json_message(self, message):
        try:
            json_data = json.loads(message.content)
            self.message_object = message
            self.event = json_data["event"]
            self.player_id = json_data["discord-id"]
            #Not sure what to do with this atm but I would imagine its something ingame
            #So for now it has a place in the message object
            self.player_uuid = json_data["player-uuid"]
            self.id = int(json_data["id"])
            self.message = json_data["message"]
            
        except json.JSONDecodeError:
            return # Skip if not JSON
        
        # The event does one of the three Cs
        event = json_data.get("event")
        if event == "create":
            return
        elif event == "claim":
            return
        elif event == "close":
            return
     
    # ok now do magic with the events   
    async def create_event(self, json_data):
        pass

    async def claim_event(self, json_data):
        pass

    async def close_event(self, json_data):
        pass