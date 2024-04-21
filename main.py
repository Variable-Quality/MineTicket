import discord
from discord import app_commands
from discord.ext import commands
import sql_interface as sql
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
    # Quick check to see if user has proper role
    staff_role = discord.utils.find(lambda r: r.name == STAFF_ROLE, interaction.guild.roles)
    if staff_role not in interaction.user.roles:
        return


    embed = discord.Embed(
        title="Want to open a new ticket?",
        description="Click the button below to start a new ticket.",
        color=discord.Color.blue(),
    )
    # Create the "Tickets" category if it doesn't exist
    ticket_category = discord.utils.get(interaction.guild.categories, name="Tickets")
    if not ticket_category:
        ticket_category = await interaction.guild.create_category("Tickets")

    # Creat the archive category
    ticket_archive = discord.utils.get(interaction.guild.categories, name="ticket-archive")
    if not ticket_archive:
        ticket_category = await interaction.guild.create_category("ticket-archive")
        
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
            INTAKE_CHANNEL, category=ticket_category, overwrites=overwrites
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

# NOTE:
# Originally we had planned to leave this command here
# However, we didn't think it made sense to spawn a modal anywhere and anywhere
# So we relegated it to just the button 
# Additionally we changed how info is taken in for tickets, almost requiring a modal
# So now its here, in a kinda graveyard.

# @tree.command(name="open_ticket", description="Opens a ticket")
# async def open_ticket(interaction: discord.Interaction):
#     await create_ticket_helper(interaction)

# May wanna rename commands to be easier to type
# Like just claim instead of claim_ticket
@tree.command(name="claim_ticket", description="Claim a support ticket")
@commands.has_role(STAFF_ROLE)
async def claim_ticket(interaction: discord.Interaction, ticket_number:int=None):
    
    await claim_ticket_helper(interaction, ticket_number)

@tree.command(name="close_ticket", description="Close the current ticket")
async def close_ticket(interaction: discord.Interaction, ticket_number:int=None):

    await close_ticket_helper(interaction, ticket_number)





bot.run(token=TOKEN)
