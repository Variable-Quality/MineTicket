import discord
from discord.ext import commands
import configparser

cfg = configparser.ConfigParser()
cfg.read("config.ini")
TOKEN = cfg["SECRET"]["token"]

class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents, **kwargs):
        super().__init__(command_prefix="!", intents=intents, case_insensitive=True)

    async def on_ready(self):
        print(f"Logged in as {self.user}!")

    async def on_message(self, message):
        print(f"Message received in #{message.channel} from {message.author}: {message.content}")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send('Invalid command. Use `!help` to see available commands.')

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)

@bot.command(name='help')
async def help_command(ctx):
    help_embed = discord.Embed(title="Help", description="List of available commands:")
    for command in bot.commands:
        help_embed.add_field(name=command.name, value=command.help, inline=False)
    await ctx.send(embed=help_embed)

@bot.command(name='open_ticket', help='Opens a ticket')
async def open_ticket(ctx: commands.Context):
    # Create a new channel named "ticket-{user_id}"
    ticket_channel_name = f"ticket-{ctx.author.id}"
    ticket_channel = await ctx.guild.create_text_channel(ticket_channel_name)

    # Send a message in the new channel
    await ticket_channel.send(f"Ticket created by {ctx.author.mention}!")

    # Reply to the user in the original channel
    await ctx.reply(content=f"Ticket is being created in {ticket_channel.mention}!")

@bot.command(name='say', help='Make the bot send a message')
async def say(ctx, *, text: str):
    await ctx.send(text)

@bot.command(name='say_fancy', help='Make the bot send a fancy message')
async def say_fancy(ctx, *, text: str):
    embed = discord.Embed(title="", description=text, color=discord.Color.purple())
    await ctx.send(embed=embed)

bot.run(TOKEN)

