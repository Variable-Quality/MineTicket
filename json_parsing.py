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
        
        # ok, now read any new message in intake
        @client.event
        async def on_message(message):
            if message.channel == channel:
                await self.parse_json_message(message)

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
            await self.create_event(json_data)
        elif event == "claim":
            await self.claim_event(json_data)
        elif event == "close":
            await self.close_event(json_data)
     
    # ok now do magic with the events   
    async def create_event(self, json_data):
        player_id = json_data["discord-id"]
        # player_uuid = json_data["player-uuid"] <-- this is that minecraft UUID, can we take that in?
        message = json_data["message"]

        # Make a ticket from this info
        # We gotta makee sure to make player_uuid makes it in next round

        # discord.Object since it needs an .Interaction
        player = sql.player_from_interaction(discord.Object(id=int(player_id)))
        entry = sql.TableEntry(
            players=str(player),
            staff="",
            message=message,
            status="open",
            table="players"
        )
        entry.push()
        # grab the ID
        ticket_id = sql.get_most_recent_entry("players", only_id=True)
        # add a message here to confirm?


    async def claim_event(self, json_data):
        ticket_id = json_data["id"]
        staff_id = json_data["discord-id"]

        entry = sql.fetch_by_id(ticket_id, "players")
        if entry:
            staff_member = sql.player_from_interaction(discord.Object(id=int(staff_id)))
            entry.involved_staff = str(staff_member)
            entry.status = "claimed"
            entry.update()
            # add a messsage to confirm?

    async def close_event(self, json_data):
        ticket_id = json_data["id"]
        player_id = json_data["discord-id"]
        message = json_data["message"]
    
        # Close the ticket with the player's information
        entry = sql.fetch_by_id(ticket_id, "players")
        if entry:
            entry.status = "closed"
            entry.message = message
            entry.update()
            # add a message here to confirm?