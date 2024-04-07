import discord
import asyncio
from discord import app_commands
from discord.ext import commands
import sql_interface as sql
import random
import ui
from configmanager import database_config_manager as db_cfm
from bot_manager import *

async def create_channel_helper(interaction: discord.Interaction, ticket_id):
    sql_entry = sql.fetch_by_id(int(ticket_id))
    players = sql_entry.involved_players_discord.split(",")
    for player in players:
        player_discord = bot.get_user(player)
        overwrites[player_discord] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True
        )

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(
            read_messages=False, send_messages=False
        ),
        interaction.user: discord.PermissionOverwrite(
            read_messages=True, send_messages=True
        ),
    }


    tickets_category = discord.utils.get(interaction.guild.categories, name="Tickets")
    ticket_channel_name = f"ticket-{ticket_id}"
    ticket_channel = await interaction.guild.create_text_channel(
        ticket_channel_name, category=tickets_category, overwrites=overwrites
    )

    # Send a message in the new channel
    await ticket_channel.send(
        f"Ticket #{ticket_id} created by {interaction.user.mention}!"
    )

    # Reply to the user in the original channel
    await interaction.response.send_message(
        content=f"Ticket #{ticket_id} is being created in {ticket_channel.mention}!",
        ephemeral=True,
    )

async def create_ticket_helper(interaction: discord.Interaction):
    # Create a new channel named "ticket-{user_id}"
    # Need to figure a new way to do this as this was a temp solve
    # Polls database and gets the next ID
    ticket_id = int(sql.get_most_recent_entry(TABLE_NAME, only_id=True)) + 1
    staff_channel = discord.utils.get(interaction.guild.channels, name=OPEN_TICKET_CHANNEL)
    # Hardcoded Dict, can't think of a way to load this from a config file
    table_dict = {
        "id": ticket_id,
        "involved_players_discord": str(interaction.user.id),
        # TODO:
        # Add logic to look up player's ingame minecraft name, or vice versa
        "involved_players_minecraft": "",
        "involved_staff_discord": "",
        "involved_staff_minecraft": "",
        "status": "open",
        # TODO:
        # Update message field with info player fills in from UI
        "message": "I'm a filler message! Yipee!!!",
    }

    # Create the ticket in sql
    ticket = sql.TableEntry(table_info=table_dict)

    # Push it!
    ticket.push()
    await interaction.response.send_message(f"Ticket {ticket_id} has been created!", ephemeral=True, delete_after=5)
    embed = discord.Embed(
        title=f"Ticket {ticket_id}",
        description=f"User: {interaction.user.name}\nDiscord ID: {interaction.user.id}\nMinecraft UUID: {ticket.involved_players_minecraft}\nDescription: {ticket.message}",
        color=discord.Color.green()
    )
    await staff_channel.send(embed=embed, view=ButtonOpen(custom_id=ticket_id))

async def claim_ticket_helper(interaction: discord.Interaction, ticket_num=None, view=None):
    # TODO:
    # Move this to be able to work in a button
    # That way we wont need to check for the category or anything since the button will show up where we want it to
    # Maybe even delete the slash command

    # Check if in ticket channel
    # Check role, ex staff
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE)
    if staff_role and staff_role in interaction.user.roles:
        if not ticket_num:
            # Grab ticket ID from the channel name
            try:
                ticket_id = int(interaction.channel.name.split("-")[1])
            except ValueError:
                print(
                    f"WARNING!!!!! TICKET {interaction.channel.name} HAS INVALID TITLE!!"
                )
                await interaction.response.send_message(
                    embed = discord.Embed(
                        description="I'm sorry, I cannot close the ticket as I cannot find the ID. Please report this error."
                    ),
                    ephemeral=True
                )
                return
        else:
            try:
                ticket_id = int(ticket_num)
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Ticket ID",
                    description=f"Ticket ID {ticket_id} is not a valid ID. Please retry with a valid ID.",
                    color= discord.Color.blue(),
                    embed=embed
                )
                await interaction.response.send_message(
                    ephemeral=True
                    )
                return
        staff_member = interaction.user.id
        # Update database logic here
        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        if len(entry.involved_staff_discord) > 0:
            staff_name = bot.get_user(staff_member).name
            await interaction.response.send_message(
                embed = discord.Embed(
                f"Ticket #{ticket_id} has already been claimed by {staff_name}.",
                ephemeral=True, embed=embed
                )
            )
            return
        entry.involved_staff_discord = str(staff_member)
        entry.status = "claimed"
        entry.update_dict()
        entry.update()
        await interaction.response.send_message(
            embed = discord.Embed(
                title="Ticket claimed",
                description=f"Ticket #{ticket_id} has been claimed by {interaction.user.mention}."
            ),
            view=ButtonClaimed(custom_id=ticket_id),
            ephemeral=False
        )
    else:
        # Non-staff reply
        await interaction.response.send_message(
            embed = discord.Embed(
                f"You need the {STAFF_ROLE} role to claim a support ticket.",
                ephemeral=True, embed=embed
            )
        )

async def close_ticket_helper(interaction: discord.Interaction, ticket_num=None):

    # Grab ticket ID from the channel name
    if not ticket_num:
        try:
            ticket_id = int(interaction.channel.name.split("-")[1])
        except ValueError:
            embed = discord.Embed(
                print(f"WARNING!!!!! TICKET {interaction.channel.name} HAS INVALID TITLE!!"), embed=embed
            )
            interaction.response.send_message(
                embed = discord.Embed(
                    "I'm sorry, I cannot close the ticket as I cannot find the ID from the title. Please report this error.", ephemeral=True, embed=embed
                )
            )
            return
    else:
        try:
            ticket_id = int(ticket_num)
        except ValueError:
            embed = discord.Embed(
                interaction.response.send_message(
                    "Please enter a valid ticket ID.", ephemeral=True, embed=embed
                )
            )
            return
    # Archive command here
    # await interaction.channel.delete()
    # Notify channel is closed, dont delete yet
    entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
    entry.status = "closed"
    curr_overwrites = interaction.channel.overwrites
    keys = list(curr_overwrites.keys())
    for key in keys[1:]:
        member = bot.get_user(int(key.id))
        await interaction.channel.set_permissions(
            member, send_messages=False, read_messages=True
        )
    entry.update_dict()
    entry.update()
    await interaction.response.send_message(
        embed = discord.Embed(
            description=f"Ticket #{ticket_id} has been closed.",
            color=discord.Color.blue()
        )
    )

"""
===========================================================================
==================================BUTTONS==================================
===========================================================================
"""


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
        ticket_id = self.ticket_id

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        # Check if the user is the claiming staff member or an added staff member

        staff_id = entry.involved_staff
        if str(interaction.user.id) != staff_id and str(interaction.user.id) not in entry.involved_players.split(","):
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
            return m.channel == interaction.channel

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

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
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

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
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
