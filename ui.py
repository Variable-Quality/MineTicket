from discord.ui import Modal, TextInput
from discord import Interaction, TextStyle, Embed, Color
from datetime import datetime
import sql_interface as sql

TABLE_NAME = "players"


class ticket_ui_create(Modal, title="Create a new ticket"):
    player_ign = TextInput(
        label="In Game Name",
        placeholder="Enter your minecraft name here",
        required=True,
        row=0,
    )
    server = TextInput(
        label="Server",
        placeholder="Server the problem is ocurring on (Vanilla, Modded, Discord)",
        required=True,
        row=1,
    )
    message = TextInput(
        label="Message",
        placeholder="Describe what the problem is",
        required=True,
        max_length=1000,
        row=2,
    )

    async def on_submit(self, interaction: Interaction):
        ticket_id = sql.get_most_recent_entry(TABLE_NAME, only_id=True) + 1
        embed = Embed(
            title=f"Ticket #{str(ticket_id)}",
            description=f"**In Game Name:** {self.player_ign.value}\n**Server:** {self.server.value}\n**Describe the problem: **{self.message.value}",
            timestamp=datetime.now(),
            color=Color.green(),
        )

        # Gets the player, creates the ticket in the SQL database
        player = sql.player_from_interaction(interaction)
        sql_entry = sql.TableEntry(
            str(player), "None", self.message.value, "open", TABLE_NAME
        )
        sql_entry.push()
        await interaction.response.send_message(embed=embed)


class ticket_ui_claim(Modal, title="Claim a ticket"):

    ticket_num = TextInput(
        label="Ticket Id", placeholder="What ticket number?", required=True, row=2
    )

    async def on_submit(self, interaction: Interaction):
        embed = Embed(
            title=f"Ticket #{str(ticket_num.value)}",
            description=f"Staff member {interaction.user.name} added to ticket {ticket_num.value}",
            timestamp=datetime.now(),
            color=Color.yellow(),
        )

        # Gets the player, creates the ticket in the SQL database
        staff = sql.player_from_interaction(interaction)
        sql_entry = sql.TableEntry(
            str(players),
            str(staff),
            staff_member,
            self.status.value,
            "claim",
            TABLE_NAME,
            int(ticket_num.value),
        )
        sql_entry.update()
        await interaction.response.send_message(embed=embed)


class ticket_ui_close(Modal, title="Close a ticket (if it exists)"):
    player_ign = TextInput(
        label="In Game Name",
        placeholder="Enter your minecraft name here",
        required=True,
        row=0,
    )
    server = TextInput(
        label="Server",
        placeholder="Server the problem is ocurring on (Vanilla, Modded, Discord)",
        required=True,
        row=1,
    )
    message = TextInput(
        label="Message",
        placeholder="Describe what the problem is",
        required=True,
        max_length=1000,
        row=2,
    )

    async def on_submit(self, interaction: Interaction):
        ticket_id = sql.get_most_recent_entry(TABLE_NAME, only_id=True) + 1
        embed = Embed(
            title=f"Ticket #{str(ticket_id)}",
            description=f"**In Game Name:** {self.player_ign.value}\n**Server:** {self.server.value}\n**Describe the problem: **{self.message.value}",
            timestamp=datetime.now(),
            color=Color.green(),
        )

        # Gets the player, creates the ticket in the SQL database
        player = sql.player_from_interaction(interaction)
        sql_entry = sql.TableEntry(
            str(player), "None", self.message.value, "open", TABLE_NAME
        )
        sql_entry.push()
        await interaction.response.send_message(embed=embed)
