import discord
from discord.ext import commands
from discord import app_commands
import json_parsing as json
from configmanager import database_config_manager as db_cfm
import sql_interface as sql

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


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = Bot(intents)
tree = app_commands.CommandTree(bot)