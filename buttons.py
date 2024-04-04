import discord
from discord import app_commands
from discord.ext import commands
import sql_interface as sql
import random
import ui
from configmanager import database_config_manager as db_cfm
from bot_manager import *

"""
What are the button states?
1. Open
    Claim
2. Claimed
    Close
    Add user
3. Closed
    Re open (open)
    Chat is unusable

"""


class ButtonOpen(discord.ui.View):
    """
    What does this button class do?
    This is attatched to messages where the ticket is in the state `Open`

    What does this add?
    Claim button
    """

    def __init__(self, *, timeout=180, custom_id=None):
        super().__init__(timeout=timeout)
        self.ticket_id = custom_id

    @discord.ui.button(label="claimButton", style=discord.ButtonStyle.green)
    async def claimButton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # https://stackoverflow.com/questions/74426018/attributeerror-button-object-has-no-attribute-response
        # We had a few attribute errors and this might be the right fix.
        await interaction.message.delete()
        await claim_ticket_helper(interaction, self.ticket_id, view=ButtonClaimed(custom_id=self.ticket_id))


class ButtonClaimed(discord.ui.View):
    """
    What does this button class do?
    This is attatched to messages where the ticket is in the state `Claim`

    What does this add?
    Close button
    Add staff button
    """

    def __init__(self, *, timeout=180, custom_id:int=None):
        super().__init__(timeout=timeout)
        self.ticket_id = custom_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red)
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Logic for closing the ticket
        ticket_channel = interaction.channel
        ticket_id = self.ticket_id

        entry = sql.fetch_by_id(ticket_id, TABLE_NAME)
        # Check if the user is the claiming staff member or an added staff member

        staff_data = entry.involved_staff.split(",")
        staff_id = staff_data[1]
        if str(interaction.user.id) != staff_id and str(
            interaction.user.id
        ) not in entry.involved_players.split(","):
            embed = discord.Embed(
                title="Unauthorized",
                description=f"You do not have permission to close this ticket.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        entry.status = "closed"
        entry.update()

        curr_overwrites = interaction.channel.overwrites
        keys = list(curr_overwrites.keys())
        for key in keys[1:]:
            member = interaction.guild.get_member(int(key.id))
            await interaction.channel.set_permissions(
                member, send_messages=False, read_messages=True
            )

        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Ticket #{ticket_id} has been closed.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, view=ButtonClosed())

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.green)
    async def add_user_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket_channel = interaction.channel
        ticket_id = int(ticket_channel.name.split("-")[1])

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        await interaction.response.send_message(
            "Please enter the user's ID or mention:", ephemeral=True
        )
        try:
            msg = await interaction.client.wait_for(
                "message", check=check, timeout=60.0
            )
            await msg.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Timed out waiting for user input.", ephemeral=True
            )
            return

        user_id = msg.content.strip("<@!>")
        try:
            user = await interaction.guild.fetch_member(int(user_id))
        except discord.NotFound:
            await interaction.followup.send(
                "Invalid user ID or mention.", ephemeral=True
            )
            return

        entry = sql.fetch_by_id(ticket_id, TABLE_NAME)
        entry.involved_players += f",{str(user)}"
        entry.update()

        await ticket_channel.set_permissions(
            user, read_messages=True, send_messages=True
        )
        await interaction.followup.send(f"{user.mention} has been added to the ticket.")


class ButtonClosed(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Reopen Ticket", style=discord.ButtonStyle.green)
    async def reopen_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket_channel = interaction.channel
        ticket_id = int(ticket_channel.name.split("-")[1])

        entry = sql.fetch_by_id(ticket_id, TABLE_NAME)
        entry.status = "open"
        entry.update()

        curr_overwrites = interaction.channel.overwrites
        keys = list(curr_overwrites.keys())
        for key in keys[1:]:
            member = interaction.guild.get_member(int(key.id))
            await interaction.channel.set_permissions(
                member, send_messages=True, read_messages=True
            )

        embed = discord.Embed(
            title="Ticket Reopened",
            description=f"Ticket #{ticket_id} has been reopened.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, view=ButtonClaimed())
