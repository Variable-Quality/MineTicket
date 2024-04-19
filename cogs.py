from bot_manager import *
from discord.ext import tasks, commands
from configmanager import database_config_manager as db_cfm
import sql_interface as sql

CONFIG_FILENAME = None
CFM = db_cfm(filename=CONFIG_FILENAME)
OPEN_TICKET_CHANNEL = CFM.cfg["BOT"]["staff_channel"]

class JSONCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        # NOTE:
        # This will only work on the first guild the bot is a member of.
        # Potentially will need to adjust this if its throwing a hissyfit
        self.staff_channel = discord.utils.get(
            bot.guilds[0].channels, name=OPEN_TICKET_CHANNEL
        )
        self.json_check.start()
        

    def cog_unload(self):
        self.json_check.cancel()

    @tasks.loop(seconds=30)
    async def json_check(self):
        # Just in case there were problems finding the staff channel
        if self.staff_channel is None:
            self.staff_channel = discord.utils.get(
                bot.guilds[0].channels, name=OPEN_TICKET_CHANNEL
            )
        json_manager = sql.json_table_manager()
        self.messages = json_manager.get_messages(self.ticket_id)
        async for message in self.staff_channel.history(limit=200):
            for msg_id in self.messages.split(","):
                if int(message.id) == int(msg_id):
                    print("Message found!")

    @json_check.before_loop
    async def before_json_check(self):
        await self.bot.wait_until_ready()