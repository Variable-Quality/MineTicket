import discord
from discord import app_commands
from discord.ext import commands
import configparser
import sql_interface
import random

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

#Command to sync commands
#Aye dawg I heard you liked commands

# This command isn't working, added sync back to startup for now
# Todo: Fix this
@bot.command(name='sync', description='Syncs command list, use only when necessary')
async def sync(interaction:discord.Interaction):
    bot.tree.clear_commands(guild=interaction.guild)
    await bot.tree.sync()
    #Testing out a new way of responding
    interaction.response.send_message("Tree Sync'd.")

# @bot.hybrid_command(name='name of the command', description='description of the command')
# async def command_name(interaction: discord.Interaction):
#        [...] The magic goes here

@bot.hybrid_command(name='open_ticket', description='Opens a ticket')
async def open_ticket(ctx: commands.Context):
    # Create a new channel named "ticket-{user_id}"
    # Need to figure a new way to do this as this was a temp solve

    # Make a tickets "folder" using Categories
    tickets_category = discord.utils.get(ctx.guild.categories, name="Tickets")
    if not tickets_category:
        tickets_category = await ctx.guild.create_category("Tickets")

    ticket_id = str(random.randint(100000, 999999))

    ticket_channel_name = f"ticket-{ticket_id}"
    ticket_channel = await ctx.guild.create_text_channel(ticket_channel_name, category=tickets_category)

    # Send a message in the new channel
    await ticket_channel.send(f"Ticket #{ticket_id} created by {ctx.author.mention}!")

    # Reply to the user in the original channel
    await ctx.reply(content=f"Ticket #{ticket_id} is being created in {ticket_channel.mention}!")


@bot.hybrid_command(name='say', description='Make the bot send message')
async def say(interaction: discord.Interaction, message:str):
    discordID = interaction.message.author.id
    uuid = interaction.message.id
    ticket = sql_interface.TableEntry("create", uuid, discordID, message,"players")
    ticket.push()
    await interaction.send(content="Ticket Created!")

@bot.hybrid_command(name="debug", description="Debug command for doing whatever you need it to do because caching is a cunt")
async def debug(interaction:discord.Interaction, text:str):
    if text == "reset all":
        sql_interface.reset_to_default()
        await interaction.send(content="Database Reset!")

@bot.hybrid_command(name='say_fancy', description='Make the bot send message but nicer')
async def say_fancy(interaction: discord.Interaction, text:str):
     embed = discord.Embed(title="", description=text, color=discord.Color.purple())
     await interaction.send(embed=embed)

@bot.hybrid_command(name='pull_ticket', description='Pulls a ticket from the database given an ID')
async def pull_ticket(interaction:discord.Interaction, ticket:str):
    try:
        id = int(ticket)
    except TypeError:
        await interaction.send(content="Incorrect input")
    try:
        data = sql_interface.fetch_by_id(id, "players")
    except IndexError:
        interaction.send(f"Invalid ticket number {id}")
    desc = f"Player-UUID: {data[2]}\nPlayer-DiscordID: {data[3]}\n\nDescription: {data[4]}"


    embed = discord.Embed(title= f"Ticket ID #{id}", description=desc, color=discord.Color.green())

    
    await interaction.send(embed=embed)

@bot.hybrid_command(name="create_ticket", description="Creates a new ticket given the information.")
async def create_ticket(interaction:discord.Interaction, event:str, message:str):
    discordID = interaction.message.author.id
    uuid = interaction.message.id
    ticket = sql_interface.TableEntry(event, uuid, discordID, message,"players")
    ticket.push()
    await interaction.send(content="Ticket Created!")


#@bot.command(name='pull_ticket', description='Pulls a ticket from the database given an ID')
#async def pull_ticket(interaction:discord.Interaction, text:str):
#    print("AAAAAAAAAAAAAAAAAAAAAAA")
#    try:
#        id = int(text)
#    except TypeError:
#        await interaction.send(content="Incorrect input")
#
#    data = sql_interface.fetch_by_id(id, "players")
#    await interaction.send(content=str(data))    

bot.run(token=TOKEN)
