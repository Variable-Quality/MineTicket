import discord
from discord.ext import commands
import uuid

# Define your Discord bot token here
TOKEN = 'your_discord_bot_token_here'

# Define your server's ticket creation channel ID here
TICKET_CHANNEL_ID = 123456789012345678

# Define your server's ticket category ID here
TICKET_CATEGORY_ID = 123456789012345678

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def create_ticket(ctx):
    # Check if the command is used in the ticket creation channel
    if ctx.channel.id != TICKET_CHANNEL_ID:
        return

    # Generate a unique ticket ID
    ticket_id = str(uuid.uuid4())

    # Create a new ticket channel
    ticket_channel = await ctx.guild.create_text_channel(f'ticket-{ticket_id}', category=discord.utils.get(ctx.guild.categories, id=TICKET_CATEGORY_ID))

    # Mention the user who created the ticket and give instructions
    await ticket_channel.send(f'Thanks for reaching out {ctx.author.mention}! A staff member will assist you shortly.')

# Run the bot with the specified token
bot.run(TOKEN)
