import discord
from discord import app_commands
from discord.ext import commands
import configparser
import sql_interface as sql
import random
import ui as bot_ui
from buttons import Buttons, ButtonOpen
import json_parsing as json

cfg = configparser.ConfigParser()
cfg.read("config.ini")
TOKEN = cfg["SECRET"]["token"]

# TODO: LOAD FROM CONFIG!!!!!!!!!!!!!
TABLE_NAME = "players"
WEBHOOK_CHANNEL = "bot_ingest"
STAFF_ROLE = "Staff"


class Bot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        # You can alternatively use ! as a command prefix instead of slash commands
        # Trying to fix as it sometimes does not work

    async def on_ready(self):
        print(f"Logged in as {self.user}!")
        # Since the sync command doesnt wanna work, fuck it
        await tree.sync()

    async def on_message(self, message):
        print(
            f"Message recieved in #{message.channel} from {message.author}: {message.content}"
        )
        # Weird issue, ephemeral messages throw an AttributeError here
        # Copy paste:
        # AttributeError: 'DMChannel' object has no attribute 'name'
        if message.channel.name == WEBHOOK_CHANNEL:
            message_json = json.message(message)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = Bot(intents)
tree = app_commands.CommandTree(bot)
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

    ticket_category = await interaction.guild.create_category("Tickets")
    ticket_channel = await interaction.guild.create_text_channel(
        "create-a-ticket", category=ticket_category
    )
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
        "Setup complete! The button is now available in the #tickets channel."
    )


@tree.command(name="open_ticket", description="Opens a ticket")
async def open_ticket(interaction: discord.Interaction):
    # Create a new channel named "ticket-{user_id}"
    # Need to figure a new way to do this as this was a temp solve

    # Make a tickets "folder" using Categories
    # I'm thinking we move this to setup so we only need to do this once.
    tickets_category = discord.utils.get(interaction.guild.categories, name="Tickets")

    # Polls database and gets the next ID
    ticket_id = int(sql.get_most_recent_entry(TABLE_NAME, True)) + 1

    # Grab player using function from sql_interface
    player = sql.player_from_interaction(interaction)

    # Create the ticket in sql
    ticket = sql.TableEntry(
        players=str(player),
        staff="",
        message=f"Ticket #{ticket_id} created by {interaction.user.mention}!",
        status="open",
        table=TABLE_NAME,
    )

    # Push it!
    ticket.push()

    # TODO:
    # Modify these overwrites when new player is added
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(
            read_messages=False, send_messages=False
        ),
        interaction.user: discord.PermissionOverwrite(
            read_messages=True, send_messages=True
        ),
    }

    ticket_channel_name = f"ticket-{ticket_id}"
    ticket_channel = await interaction.guild.create_text_channel(
        ticket_channel_name, category=tickets_category, overwrites=overwrites
    )

    # Send a message in the new channel
    # TODO - add a channel link in the text
    embed = discord.Embed(
        title="Ticket created!",
        description=f"Ticket #{ticket_id} created by {interaction.user.mention}!",
        color=discord.Color.blue(),
    )
    await ticket_channel.send(embed=embed, view=ButtonOpen())

    # Reply to the user in the original channel
    await interaction.response.send_message(embed=embed, ephemeral=True)


# May wanna rename commands to be easier to type
# Like just claim instead of claim_ticket
@tree.command(
    name="claim_ticket", description="Claim a support ticket as a staff member"
)
async def claim_ticket(interaction: discord.Interaction):
    # Check if in ticket channel
    if interaction.channel.category and interaction.channel.category.name == "Tickets":
        # Check role, ex staff
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE)

        if staff_role and staff_role in interaction.user.roles:
            # Grab ticket ID from the channel name
            try:
                ticket_id = int(interaction.channel.name.split("-")[1])
            except ValueError:
                print(
                    f"WARNING!!!!! TICKET {interaction.channel.name} HAS INVALID TITLE!!"
                )
                interaction.response.send_message(
                    "I'm sorry, I cannot close the ticket as I cannot find the ID from the title. Please report this error."
                )
                return

            staff_member = sql.player_from_interaction(interaction)
            # Update database logic here
            entry = sql.fetch_by_id(ticket_id, TABLE_NAME)

            if len(entry.involved_staff) > 0:
                staff_name = entry.involved_staff.split(",")[0]
                interaction.response.send_message(
                    f"Ticket #{ticket_id} has already been claimed by {staff_name}.",
                    ephemeral=True,
                )
                return

            entry.involved_staff = str(staff_member)
            entry.status = "claimed"
            entry.update()
            await interaction.response.send_message(
                f"Ticket #{ticket_id} has been claimed by {interaction.user.mention}."
            )

        else:
            # Non-staff reply
            await interaction.response.send_message(
                f"You need the {STAFF_ROLE} role to claim a support ticket.",
                ephemeral=True,
            )

    else:
        # Non-ticket channel reply
        await interaction.response.send_message(
            "This command can only be used in a ticket channel.", ephemeral=True
        )


@tree.command(name="close_ticket", description="Close the current ticket")
async def close_ticket(interaction: discord.Interaction):
    # Check if in a ticket channel
    if interaction.channel.category and interaction.channel.category.name == "Tickets":
        # Grab ticket ID from the channel name
        try:
            ticket_id = int(interaction.channel.name.split("-")[1])
        except ValueError:
            print(f"WARNING!!!!! TICKET {interaction.channel.name} HAS INVALID TITLE!!")
            interaction.response.send_message(
                "I'm sorry, I cannot close the ticket as I cannot find the ID from the title. Please report this error."
            )
            return
        # Archive command here

        # await interaction.channel.delete()
        # Notify channel is closed, dont delete yet
        entry = sql.fetch_by_id(ticket_id, TABLE_NAME)
        entry.status = "closed"

        curr_overwrites = interaction.channel.overwrites
        keys = list(curr_overwrites.keys())
        for key in keys[1:]:
            print(f"MEMBER ID: {key.id}")
            member = bot.get_user(int(key.id))
            await interaction.channel.set_permissions(
                member, send_messages=False, read_messages=True
            )
        entry.update()
        await interaction.response.send_message(
            f" Ticket #{ticket_id} has been closed."
        )

    else:
        # Catch non-ticket channels
        await interaction.message.reply(
            "This command can only be used in a ticket channel."
        )


# Uselsss function
@tree.command(name="list_tickets", description="List all open support tickets")
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
