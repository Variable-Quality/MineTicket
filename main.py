import discord
from discord import app_commands
from discord.ext import commands
import sql_interface as sql
import ui as bot_ui
from buttons import Buttons
import json_parsing as json
from configmanager import database_config_manager as db_cfm

CONFIG_FILENAME = None
CFM = db_cfm(filename=CONFIG_FILENAME)
TOKEN = CFM.cfg["BOT"]["token"]
print(TOKEN)
TABLE_NAME = CFM.cfg["DATABASE"]["table"]
WEBHOOK_CHANNEL = CFM.cfg["BOT"]["ingest_channel"]
INTAKE_CHANNEL = CFM.cfg["BOT"]["intake_channel"]
STAFF_ROLE = CFM.cfg["BOT"]["staff_role"]


class Bot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        # You can alternatively use ! as a command prefix instead of slash commands
        # Trying to fix as it sometimes does not work
        self.json_parser = None

    async def on_ready(self):
        print(f"Logged in as {self.user}!")
        # Since the sync command doesnt wanna work, fuck it
        await tree.sync()

        # Initialize the ParseJSON instance inside on_ready
        if self.guilds:
            self.json_parser = json.ParseJSON(self, self.guilds[0])
        else:
            print("No guilds found. JSON parsing functionality will not be available.")

    async def on_message(self, message):
        print(
            f"Message recieved in #{message.channel} from {message.author}: {message.content}"
        )
        # Weird issue, ephemeral messages throw an AttributeError here
        # Copy paste:
        # AttributeError: 'DMChannel' object has no attribute 'name'
        if message.channel.name == WEBHOOK_CHANNEL:
            message_json = json.message(message)
        if message.channel.name == INTAKE_CHANNEL and self.json_parser is not None:
            # Call the JSON parsing function
            await self.json_parser.parse_json_message(message)


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

    manager = SQLManager()
    table_data = CFM.cfg["TABLE"]
    manager.create_table(CFM.cfg["DATABASE"]["table"], table_data)

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
    # Create a new channel named "ticket-{user_id}"
    # Need to figure a new way to do this as this was a temp solve

    # Make a tickets "folder" using Categories
    # I'm thinking we move this to setup so we only need to do this once.
    tickets_category = discord.utils.get(interaction.guild.categories, name="Tickets")

    # Polls database and gets the next ID
    ticket_id = int(sql.get_most_recent_entry(TABLE_NAME, True)) + 1

    # Grab player using function from sql_interface
    player = sql.player_from_interaction(interaction)

    # Hardcoded Dict, can't think of a way to load this from a config file
    table_dict = {
        "id": None,
        "involved_players_discord": str(player).split(",")[1],
        # TODO:
        # Add logic to look up player's ingame minecraft name, or vice versa
        "involved_players_minecraft": "",
        "involved_staff_discord": "",
        "involved_staff_minecraft": "",
        "status": "open",
        # TODO:
        # Update message field with info player fills in from UI
        "message": "I'm a filler message! Yipee!!!",
    }

    # Create the ticket in sql
    ticket = sql.TableEntry(table_info=table_dict)

    # Push it!
    ticket.push()

    # TODO:
    # Modify these overwrites when new player is added
    # Move this entire chunk of code to a "Create channel" function rather than here
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
    await ticket_channel.send(
        f"Ticket #{ticket_id} created by {interaction.user.mention}!"
    )

    # Reply to the user in the original channel
    await interaction.response.send_message(
        content=f"Ticket #{ticket_id} is being created in {ticket_channel.mention}!",
        ephemeral=True,
    )


# May wanna rename commands to be easier to type
# Like just claim instead of claim_ticket
@tree.command(
    name="claim_ticket", description="Claim a support ticket as a staff member"
)
async def claim_ticket(interaction: discord.Interaction):
    # TODO:
    # Move this to be able to work in a button
    # That way we wont need to check for the category or anything since the button will show up where we want it to
    # Maybe even delete the slash command

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
            entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)

            if len(entry.involved_staff_discord) > 0:
                staff_name = entry.involved_staff_discord.split(",")[0]
                await interaction.response.send_message(
                    f"Ticket #{ticket_id} has already been claimed by {staff_name}.",
                    ephemeral=True,
                )
                return

            entry.involved_staff_discord = str(staff_member)
            entry.status = "claimed"
            entry.update_dict()
            entry.update()
            await interaction.response.send_message(
                f"Ticket #{ticket_id} has been claimed by {interaction.user.mention}.",
                ephemeral=False,
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
        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        entry.status = "closed"

        curr_overwrites = interaction.channel.overwrites
        keys = list(curr_overwrites.keys())
        for key in keys[1:]:
            print(f"MEMBER ID: {key.id}")
            member = bot.get_user(int(key.id))
            await interaction.channel.set_permissions(
                member, send_messages=False, read_messages=True
            )
        entry.update_dict()
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
