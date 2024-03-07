import discord
from discord import app_commands
from discord.ext import commands
import configparser
import sql_interface as sql
import random
import ui as bot_ui

cfg = configparser.ConfigParser()
cfg.read("config.ini")
TOKEN = cfg["SECRET"]["token"]

#TODO: LOAD FROM CONFIG!!!!!!!!!!!!!
TABLE_NAME = "players"
class Bot(discord.Client):
    def __init__(self, intents):
         super().__init__(intents=intents)
         # You can alternatively use ! as a command prefix instead of slash commands
         # Trying to fix as it sometimes does not work

    async def on_ready(self):
        print(f"Logged in as {self.user}!")
        #Bad, no, no sync on ready!
        #await self.tree.sync()

    async def on_message(self, message):
        print(f"Message recieved in #{message.channel} from {message.author}: {message.content}")


    


intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents)
tree = app_commands.CommandTree(bot)
#Command to sync commands
#Aye dawg I heard you liked commands

# This command isn't working, added sync back to startup for now
# Todo: Fix this
# Found a way to fix it - https://stackoverflow.com/questions/74413367/how-to-sync-slash-command-globally-discord-py
@tree.command(name='sync', description='Syncs command list, use only when necessary')
async def sync(interaction:discord.Interaction):
    bot.tree.clear_commands(guild=interaction.guild)
    await bot.tree.sync()
    #Testing out a new way of responding
    interaction.response.send_message("Tree Sync'd.")

# @bot.hybrid_command(name='name of the command', description='description of the command')
# async def command_name(interaction: discord.Interaction):
#        [...] The magic goes here

@tree.command(name='open_ticket', description='Opens a ticket')
async def open_ticket(ctx: commands.Context):
    # Create a new channel named "ticket-{user_id}"
    # Need to figure a new way to do this as this was a temp solve

    # Make a tickets "folder" using Categories
    tickets_category = discord.utils.get(ctx.guild.categories, name="Tickets")
    if not tickets_category:
        try:
            tickets_category = await ctx.guild.create_category("Tickets")
        except Exception as e:
            print(f"I tried to make the needed category but something went wrong!\n{e}")
            return
        print("WARNING!!! Ticket category not found! I've made one for you, but you may want to move it!")

    #Polls database and gets the next ID
    ticket_id = int(sql.get_most_recent_entry(TABLE_NAME, True)) + 1

    ticket_channel_name = f"ticket-{ticket_id}"
    ticket_channel = await ctx.guild.create_text_channel(ticket_channel_name, category=tickets_category)

    # Send a message in the new channel
    await ticket_channel.send(f"Ticket #{ticket_id} created by {ctx.author.mention}!")

    # Reply to the user in the original channel
    await ctx.reply(content=f"Ticket #{ticket_id} is being created in {ticket_channel.mention}!")

@tree.command(name='claim_ticket', description='Claim a support ticket as a staff member')
async def claim_ticket(ctx: commands.Context):
    # Check if in ticket channel
    if ctx.channel.category and ctx.channel.category.name == "Tickets":
        # Check role, ex staff
        staff_role = discord.utils.get(ctx.guild.roles, name="Staff")

        if staff_role and staff_role in ctx.author.roles:
            # Grab ticket ID from the channel name
            ticket_id = ctx.channel.name.split("-")[1]

            # Update database logic here
            
            await ctx.send(f"Ticket #{ticket_id} has been claimed by {ctx.author.mention}.")

        else:
            # Non-staff reply
            await ctx.reply("You need the 'Staff' role to claim a support ticket.")

    else:
        # Non-ticket channel reply
        await ctx.reply("This command can only be used in a ticket channel.")

@tree.command(name='close_ticket', description='Close the current ticket')
async def close_ticket(ctx: commands.Context):
    # Check if in a ticket channel
    if ctx.channel.category and ctx.channel.category.name == "Tickets":
        # Grab ticket ID from the channel name
        ticket_id = ctx.channel.name.split("-")[1]

        # Archive command here

        await ctx.channel.delete()
        # Alert mod in DMs
        await ctx.author.send(f" #{ticket_id} has been closed.")

    else:
        # Catch non-ticket channels
        await ctx.reply("This command can only be used in a ticket channel.")

@tree.command(name='list_tickets', description='List all open support tickets')
async def list_tickets(ctx: commands.Context):
    # Grab live tickets from DB
    open_tickets = None # (Something like SELECT (["1", "2", "3"]))

    if not open_tickets:
        await ctx.reply("No open tickets found.")
        return

    # Create an embed to display ticket information
    embed = discord.Embed(title="Open Support Tickets", color=discord.Color.orange())

    # Add ticket fields in here
    # for ticket in open_tickets:
    #    None = ticket
    #    embed.add_field()

    await ctx.reply(embed=embed)

@tree.command(name='say', description='Make the bot send message')
async def say(interaction: discord.Interaction, message:str):
    discordID = interaction.message.author.id
    uuid = interaction.message.id
    ticket = sql.TableEntry("create", uuid, discordID, message,"players")
    ticket.push()
    await interaction.send(content="Ticket Created!")

#Will be removed with final version
@tree.command(name="debug", description="Debug command for doing whatever you need it to do because caching is a cunt")
async def debug(interaction:discord.Interaction, text:str):
    if text == "reset all":
        sql.reset_to_default()
        await interaction.send(content="Database Reset!")

    if text == "ui":
        await interaction.response.send_modal(bot_ui.ticket_ui())

@tree.command(name='say_fancy', description='Make the bot send message but nicer')
async def say_fancy(interaction: discord.Interaction, text:str):
     embed = discord.Embed(title="", description=text, color=discord.Color.purple())
     await interaction.send(embed=embed)

@tree.command(name='pull_ticket', description='Pulls a ticket from the database given an ID')
async def pull_ticket(interaction:discord.Interaction, ticket:str):
    try:
        id = int(ticket)
    except TypeError:
        await interaction.send(content="Incorrect input")
    try:
        data = sql.fetch_by_id(id, "players")
    except IndexError:
        interaction.send(f"Invalid ticket number {id}")
    desc = f"Player-UUID: {data[2]}\nPlayer-DiscordID: {data[3]}\n\nDescription: {data[4]}"


    embed = discord.Embed(title= f"Ticket ID #{id}", description=desc, color=discord.Color.green())

    
    await interaction.send(embed=embed)

#Redundant! Remove!
@tree.command(name="create_ticket", description="Creates a new ticket given the information.")
async def create_ticket(interaction:discord.Interaction, event:str, message:str):
    discordID = interaction.message.author.id
    uuid = interaction.message.id
    ticket = sql.TableEntry(event, uuid, discordID, message,"players")
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
