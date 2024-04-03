import discord
from discord import app_commands
from discord.ext import commands
import sql_interface as sql
import ui as bot_ui
from buttons import Buttons
import json_parsing as json
from configmanager import database_config_manager as db_cfm
from bot_manager import *

CONFIG_FILENAME = None
CFM = db_cfm(filename=CONFIG_FILENAME)
TOKEN = CFM.cfg["BOT"]["token"]
TABLE_NAME = CFM.cfg["DATABASE"]["table"]
WEBHOOK_CHANNEL = CFM.cfg["BOT"]["ingest_channel"]
INTAKE_CHANNEL = CFM.cfg["BOT"]["intake_channel"]
STAFF_ROLE = CFM.cfg["BOT"]["staff_role"]

# Command to sync commands
# Aye dawg I heard you liked commands


# This command isn't working, added sync back to startup for now
# Todo: Fix this
# Found a way to fix it - https://stackoverflow.com/questions/74413367/how-to-sync-slash-command-globally-discord-py
@tree.command(name="sync", description="Syncs command list, use only when necessary")
async def sync(interaction: discord.Interaction):
    tree.clear_commands(guild=interaction.guild)
    await tree.sync()
    # Testing out a new way of responding
    interaction.response.send_message("Tree Sync'd.")


# @bot.hybrid_command(name='name of the command', description='description of the command')
# async def command_name(interaction: discord.Interaction):
#        [...] The magic goes here


@tree.command(name="run_setup", description="Starts the setup process")
async def run_setup(interaction: discord.Interaction):
    # Check if the command is used in the correct channel
    embed = discord.Embed(
        title="Want to start a ticket?",
        description="Click the button below to start a new ticket.",
        color=discord.Color.blue(),
    )

    # Create the "Tickets" category if it doesn't exist
    ticket_category = discord.utils.get(interaction.guild.categories, name="Tickets")
    if not ticket_category:
        ticket_category = await interaction.guild.create_category("Tickets")

    # Create the "Mineticket Feed" channel within the "Tickets" category if it doesn't exist
    mineticket_feed_channel = discord.utils.get(
        ticket_category.channels, name="Mineticket Feed"
    )
    if not mineticket_feed_channel:
        mineticket_feed_channel = await interaction.guild.create_text_channel(
            "Mineticket Feed", category=ticket_category
        )

    # Create the "create-a-ticket" channel within the "Tickets" category if it doesn't exist
    ticket_channel = discord.utils.get(ticket_category.channels, name="create-a-ticket")
    if not ticket_channel:
        ticket_channel = await interaction.guild.create_text_channel(
            "create-a-ticket", category=ticket_category
        )

    table = sql.Table(config=CFM.filename)
    table.push()

    # Create a Buttons instance via buttons.py
    buttons = Buttons()
    # Add button
    buttons.add_item(
        discord.ui.Button(style=discord.ButtonStyle.primary, label="Start A Ticket")
    )
    # Send message with button
    await ticket_channel.send(embed=embed, view=buttons)

    # Send confirmation
    await interaction.response.send_message(
        "Setup complete! The button is now available in the #create-a-ticket channel."
    )


@tree.command(name="open_ticket", description="Opens a ticket")
async def open_ticket(interaction: discord.Interaction):

    await create_ticket_helper(interaction)

# May wanna rename commands to be easier to type
# Like just claim instead of claim_ticket
@tree.command(
    name="claim_ticket", description="Claim a support ticket as a staff member"
)
async def claim_ticket(interaction: discord.Interaction, ticket_num:int=None):
    
    await claim_ticket_helper(interaction, ticket_num)


@tree.command(name="close_ticket", description="Close the current ticket")
async def close_ticket(interaction: discord.Interaction, ticket_num:int=None):

    await close_ticket_helper(interaction, ticket_num)


# Uselsss function
@tree.command(name="list_tickets", description="List all open support tickets")
async def list_tickets(ctx: commands.Context):
    # Grab live tickets from DB
    open_tickets = None  # (Something like SELECT (["1", "2", "3"]))

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


# Will be removed with final version
@tree.command(
    name="debug",
    description="Debug command for doing whatever you need it to do because caching is a cunt",
)
async def debug(interaction: discord.Interaction, text: str):
    if text == "reset all":
        sql.reset_to_default()
        await interaction.response.send_message("Database Reset!")

    if text == "recent":
        entry = sql.get_most_recent_entry(TABLE_NAME)
        await interaction.response.send_message(str(entry))

    if text == "ui":
        await interaction.response.send_modal(bot_ui.ticket_ui_create())

    if text == "setup":
        if interaction.channel.name == "create-a-ticket":
            # Create an embed message
            embed = discord.Embed(
                title="Want to start a ticket?",
                description="Click the button below to start a new ticket.",
                color=discord.Color.blue(),
            )
            # Create a Buttons instance via buttons.py
            buttons = Buttons()
            # Add button
            buttons.add_item(
                discord.ui.Button(
                    style=discord.ButtonStyle.primary, label="Start A Ticket"
                )
            )
            # Send message with button
            await interaction.channel.send(embed=embed, view=buttons)

            # Send confirmation
            await interaction.channel.send(
                "Setup complete! The button is now available in the #tickets channel."
            )
        else:
            await interaction.channel.send("Whoopsie doo")




bot.run(token=TOKEN)
