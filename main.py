import discord
from discord.ext import commands
import configparser

cfg = configparser.ConfigParser()
cfg.read("config.ini")
TOKEN = cfg["SECRET"]["token"]

class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents, **kwargs):
         super().__init__(command_prefix="!", intents=intents, case_insensitive=True)
         # You can alternatively use ! as a command prefix instead of slash commands
         # Trying to fix as it sometimes does not work

    async def on_ready(self):
        print(f"Logged in as {self.user}!")
        await self.tree.sync()

    async def on_message(self, message):
        print(f"Message recieved in #{message.channel} from {message.author}: {message.content}")

    


intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)


# @bot.hybrid_command(name='name of the command', description='description of the command')
# async def command_name(interaction: discord.Interaction):
#        [...] The magic goes here

@bot.hybrid_command(name='open_ticket', description='Opens a ticket')
async def open_ticket(ctx: commands.Context):
    # Create a new channel named "ticket-{user_id}"
    ticket_channel_name = f"ticket-{ctx.author.id}"
    ticket_channel = await ctx.guild.create_text_channel(ticket_channel_name)

    # Send a message in the new channel
    await ticket_channel.send(f"Ticket created by {ctx.author.mention}!")

    # Reply to the user in the original channel
    await ctx.reply(content=f"Ticket is being created in {ticket_channel.mention}!")


@bot.hybrid_command(name='say', description='Make the bot send message')
async def say(interaction: discord.Interaction, text:str):
     await interaction.send(content=text)

@bot.hybrid_command(name='say_fancy', description='Make the bot send message but nicer')
async def say_fancy(interaction: discord.Interaction, text:str):
     embed = discord.Embed(title="", description=text, color=discord.Color.purple())
     await interaction.send(embed=embed)

bot.run(token=TOKEN)

