import discord
from discord import app_commands
from discord.ext import commands
import sql_interface as sql
import ui as bot_ui
import json_parsing as json
from configmanager import database_config_manager as db_cfm
from bot_manager import *


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


@tree.command(name="setup", description="Starts the setup process")
# Decorator to restrict this command to staff only
# NOTE: Role is case sensitive
@commands.has_role(STAFF_ROLE)
async def run_setup(interaction: discord.Interaction):
    """
    Setup command to be run once the bot joins a server for the first time.

    Creates necessary category, channels, and sends the initial message with a button to create tickets.
    """
    embed = discord.Embed(
        title="Want to open a new ticket?",
        description="Click the button below to start a new ticket.",
        color=discord.Color.blue(),
    )
    # Create the "Tickets" category if it doesn't exist
    ticket_category = discord.utils.get(interaction.guild.categories, name="Tickets")
    if not ticket_category:
        ticket_category = await interaction.guild.create_category("Tickets")

    # Create the json recieving channel within the "Tickets" category if it doesn't exist
    mineticket_feed_channel = discord.utils.get(
        ticket_category.channels, name=INTAKE_CHANNEL
    )
    if not mineticket_feed_channel:
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False, send_messages=False
            )
        }
        # NOTE:
        # This channel is hidden unless the user has admin priv
        mineticket_feed_channel = await interaction.guild.create_text_channel(
            INTAKE_CHANNEL, category=ticket_category
        )

    # Create the "create-a-ticket" channel within the "Tickets" category if it doesn't exist
    # This is the one channel name that is hardcoded.
    ticket_channel = discord.utils.get(ticket_category.channels, name="create-a-ticket")
    if not ticket_channel:
        ticket_channel = await interaction.guild.create_text_channel(
            "create-a-ticket", category=ticket_category
        )

    staff_channel = discord.utils.get(ticket_category.channels, name=OPEN_TICKET_CHANNEL)
    if not staff_channel:
        role_found = False
        for role in interaction.guild.roles:
            if STAFF_ROLE in str(role.name):
                s_role = role
                role_found = True

        if not role_found:
            # There would probably be errors elsewhere if the STAFF_ROLE cannot be found
            # But just in case
            embed = discord.Embed(
                title="STAFF_ROLE Error",
                description=f"Unable to find role {STAFF_ROLE} within guild roles. Setup aborted. \nEnsure config file capitalization matches role capitalization and run /setup again.",
                color=discord.Color.red()
            )
            interaction.response.send_message(embed=embed, ephemeral=True)
            return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False, send_messages=False
            ),
            s_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=False
            )
        }
        staff_channel = await interaction.guild.create_text_channel(
            #NOTE:
            # Staff channel may want to be elsewhere
            # But it'll be alright to allow them to move it wherever they like after its created
            OPEN_TICKET_CHANNEL, category=ticket_category, overwrites=overwrites
        )
    table = sql.Table(config=CONFIG_FILENAME)
    table.push()
    # Create a DynamicButton instance via bot_managers.py
    view = discord.ui.View()
    create_ticket_button = DynamicButton(ticket_id=1, button_type="open", button_style=discord.ButtonStyle.gray)
    view.add_item(create_ticket_button)
    await ticket_channel.send(embed=embed, view=view)

    # Send confirmation
    embed = discord.Embed(
        title="Setup Complete!",
        description=f"All necessary channels have been successfully created, and a message has been sent in {ticket_channel.mention} to allow users to create tickets.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@tree.command(name="open_ticket", description="Opens a ticket")
async def open_ticket(interaction: discord.Interaction):
    await create_ticket_helper(interaction)

# May wanna rename commands to be easier to type
# Like just claim instead of claim_ticket
@tree.command(name="claim_ticket", description="Claim a support ticket")
@commands.has_role(STAFF_ROLE)
async def claim_ticket(interaction: discord.Interaction, ticket_number:int=None):
    
    await claim_ticket_helper(interaction, ticket_number)

@tree.command(name="close_ticket", description="Close the current ticket")
async def close_ticket(interaction: discord.Interaction, ticket_number:int=None):

    await close_ticket_helper(interaction, ticket_number)

# Uselsss function
@tree.command(name="list_tickets", description="List all open support tickets")
@commands.has_role(STAFF_ROLE)
async def list_tickets(interaction: discord.Interaction):
    """# Grab live tickets from DB
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

    await ctx.reply(embed=embed)"""
    open_tickets = sql.fetch_by_status("open", TABLE_NAME)
    claimed_tickets = sql.fetch_by_status("claimed", TABLE_NAME)

    if not open_tickets and not claimed_tickets:
        await interaction.response.send_message("No open or claimed tickets found.")
        return

    embed = discord.Embed(title="Support Tickets", color=discord.Color.orange())

    for ticket in open_tickets:
        embed.add_field(
            name=f"Ticket #{ticket.id} (Open)",
            value=f"Started by: {ticket.involved_players.split(',')[0]}\nAdded users: {', '.join(ticket.involved_players.split(',')[1:])}",
            inline=False,
        )

    for ticket in claimed_tickets:
        embed.add_field(
            name=f"Ticket #{ticket.id} (Claimed)",
            value=f"Started by: {ticket.involved_players.split(',')[0]}\nAdded users: {', '.join(ticket.involved_players.split(',')[1:])}\nClaimed by: {ticket.involved_staff.split(',')[0]}",
            inline=False,
        )

    await interaction.response.send_message(embed=embed)



# Will be removed with final version
@tree.command(name="debug",description="Debug command for doing whatever you need it to do because caching is a cunt")
async def debug(interaction: discord.Interaction, text: str):
    if text == "reset all":
        sql.reset_to_default(debug_entry=True)
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
            #buttons = Buttons()
            # Add button
            #buttons.add_item(
            #    discord.ui.Button(
            #        style=discord.ButtonStyle.primary, label="Start A Ticket"
            #    )
            #)
            # Send message with button
            await interaction.channel.send(embed=embed)

            # Send confirmation
            await interaction.channel.send(
                "Setup complete! The button is now available in the #tickets channel."
            )
        else:
            await interaction.channel.send("Whoopsie doo")

    if text == "button":
        await interaction.response.send_message("I'm a button message!", view=ButtonOpen(custom_id=7))

    if text == "dynamic":
        # b = return_button("Claim", "button:open:1")
        view = discord.ui.View(timeout=None)
        view.add_item(DynamicButton(ticket_id=2, button_type="channel"))
        await interaction.response.send_message("My button should open a ticket for ticket 2 because ticket 1 is a debug entry and wont work!", view=view)
        message = await interaction.original_response()
        print(discord.ui.View.from_message(message).children[0])





bot.run(token=TOKEN)
