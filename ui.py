from discord.ui import Modal, TextInput
from discord import Interaction, TextStyle, Embed, Color
from datetime import datetime
import sql_interface as sql

TABLE_NAME = "players"

class ticket_ui(Modal, title="Create a new ticket"):
    player_ign = TextInput(label="In Game Name", placeholder="Enter your minecraft name here", required=True, row=0)
    server = TextInput(label="Server", placeholder="Server the problem is ocurring on (Vanilla, Modded, Discord)", required=True, row=1)
    message = TextInput(label="Message", placeholder="Describe what the problem is", required=True, max_length=1000, row=2)

    async def on_submit(self, interaction: Interaction):
        ticket_id = sql.get_most_recent_entry(TABLE_NAME, only_id=True)+1
        embed = Embed(
            title=f"Ticket #{str(ticket_id)}",
            description=f"**In Game Name:** {self.player_ign.value}\n**Server:** {self.server.value}\n**Describe the problem: **{self.message.value}",
            timestamp=datetime.now(),
            color=Color.green()
            )
        
        #Gets the player, creates the ticket in the SQL database
        player = sql.player_from_interaction(interaction)
        sql_entry = sql.TableEntry(str(player), "None", self.message.value, "open", TABLE_NAME)
        sql_entry.push()
        await interaction.response.send_message(embed=embed)





