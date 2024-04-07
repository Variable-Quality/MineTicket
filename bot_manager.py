import discord
from discord.ext import commands
from discord import app_commands
import json_parsing as json
from configmanager import database_config_manager as db_cfm
import sql_interface as sql
from buttons import ButtonOpen, ButtonClaimed, ButtonClosed

CONFIG_FILENAME = None
CFM = db_cfm(filename=CONFIG_FILENAME)
TOKEN = CFM.cfg["BOT"]["token"]
TABLE_NAME = CFM.cfg["DATABASE"]["table"]
INTAKE_CHANNEL = CFM.cfg["BOT"]["intake_channel"]
STAFF_ROLE = CFM.cfg["BOT"]["staff_role"]
OPEN_TICKET_CHANNEL = CFM.cfg["BOT"]["staff_channel"]
#TODO:
# Add Ticket Channel on Setup

class Bot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        # You can alternatively use ! as a command prefix instead of slash commands
        # Trying to fix as it sometimes does not work
        self.json_parser = None

    async def on_ready(self):
        print(f"Logged in as {self.user}!")
        # Since the sync command doesnt wanna work, fuck it
        await tree.sync()

        # Initialize the ParseJSON instance inside on_ready
        if self.guilds:
            self.json_parser = json.ParseJSON(self, self.guilds[0])
        else:
            print("No guilds found. JSON parsing functionality will not be available.")

    async def on_message(self, message):
        if type(message.channel) is discord.DMChannel:
            return
        print(
            f"Message recieved in #{message.channel} from {message.author}: {message.content}"
        )
        # Weird issue, ephemeral messages throw an AttributeError here
        # Copy paste:
        # AttributeError: 'DMChannel' object has no attribute 'name'
        if message.channel.name == INTAKE_CHANNEL and self.json_parser is not None:
            # Call the JSON parsing function
            await self.json_parser.parse_json_message(message)

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
    await staff_channel.send(embed=embed, view=ButtonOpen())

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
                interaction.response.send_message(
                    "I'm sorry, I cannot close the ticket as I cannot find the ID. Please report this error.", ephemeral=True
                )
                return
        else:
            try:
                ticket_id = int(ticket_num)
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Ticket ID",
                    description=f"Ticket ID {ticket_id} is not a valid ID. Please retry with a valid ID.",
                    color= discord.Color.blue()
                )
                interaction.response.send_message(
                    embed=embed, ephemeral=True
                    )
                return
        staff_member = interaction.user.id
        # Update database logic here
        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        if len(entry.involved_staff_discord) > 0:
            staff_name = bot.get_user(staff_member).name
            await interaction.response.send_message(
                f"Ticket #{ticket_id} has already been claimed by {staff_name}.",
                ephemeral=True,
            )
            return
        entry.involved_staff_discord = str(staff_member)
        entry.status = "claimed"
        entry.update_dict()
        entry.update()
        await interaction.response.send_message(
            f"Ticket #{ticket_id} has been claimed by {interaction.user.mention}.",
            ephemeral=False,
            view=view
        )
    else:
        # Non-staff reply
        await interaction.response.send_message(
            f"You need the {STAFF_ROLE} role to claim a support ticket.",
            ephemeral=True,
        )

async def close_ticket_helper(interaction: discord.Interaction, ticket_num=None):

    # Grab ticket ID from the channel name
    if not ticket_num:
        try:
            ticket_id = int(interaction.channel.name.split("-")[1])
        except ValueError:
            print(f"WARNING!!!!! TICKET {interaction.channel.name} HAS INVALID TITLE!!")
            interaction.response.send_message(
                "I'm sorry, I cannot close the ticket as I cannot find the ID from the title. Please report this error.", ephemeral=True
            )
            return
    else:
        try:
            ticket_id = int(ticket_num)
        except ValueError:
            interaction.response.send_message(
                "Please enter a valid ticket ID.", ephemeral=True
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
        f" Ticket #{ticket_id} has been closed."
    )


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = Bot(intents)
tree = app_commands.CommandTree(bot)