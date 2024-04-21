import asyncio
from typing import Type
import discord
from discord.ext import commands
from discord import app_commands
import json_parsing as json
from configmanager import database_config_manager as db_cfm
import sql_interface as sql
import re

CONFIG_FILENAME = None
CFM = db_cfm(filename=CONFIG_FILENAME)
TOKEN = CFM.cfg["BOT"]["token"]
TABLE_NAME = CFM.cfg["DATABASE"]["table"]
INTAKE_CHANNEL = CFM.cfg["BOT"]["intake_channel"]
STAFF_ROLE = CFM.cfg["BOT"]["staff_role"]
OPEN_TICKET_CHANNEL = CFM.cfg["BOT"]["staff_channel"]

# Unused, is the guild ID of our test server
SERVER_ID = 1207398486933508147
class Bot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        # You can alternatively use ! as a command prefix instead of slash commands
        # Trying to fix as it sometimes does not work
        self.json_parser = None

    async def on_ready(self):
        print(f"Logged in as {self.user}!")
        await tree.sync()

        # Initialize the ParseJSON instance inside on_ready
        if self.guilds:
            self.json_parser = json.ParseJSON(self, self.guilds[0])
        else:
            print("No guilds found. JSON parsing functionality will not be available.")

    async def on_message(self, message):
        # Fix for ephemeral messages throwing errors
        if type(message.channel) is discord.DMChannel:
            return
        print(
            f"Message recieved in #{message.channel} from {message.author}: {message.content}"
        )
        if message.channel.name == INTAKE_CHANNEL and self.json_parser is not None:
            # Call the JSON parsing function
            await self.json_parser.parse_json_message(message)

    async def setup_hook(self) -> None:
        # Makes DynamicButton a persistent class
        # Avoids a lot of hassle with persistent views
        self.add_dynamic_items(DynamicButton)

def find_user(name, members: list):
    for member in members:
        if member.nick is not None:
            if member.nick.lower() == name.lower():
                return member
        else:
            if member.name.lower() == name.lower():
                return member
    
    return None

async def add_user_helper(interaction: discord.Interaction, ticket_id):

    # This assumes the interaction takes place inside of the ticket channel
    # Oh well!
    channel = interaction.channel
    def check(m):
        return m.channel == interaction.channel
    
    await interaction.response.send_message(
        "Please enter the user's ID, nickname, or mention:", ephemeral=True
    )

    try:
        msg = await interaction.client.wait_for(
            "message", check=check, timeout=60.0
        )
        await msg.delete()
    except asyncio.TimeoutError:
        await interaction.followup.send(
            "Timed out waiting for user input.", ephemeral=True
        )
        return
    
    mem = find_user(msg.content, interaction.guild.members)
    if mem == None:
        user_id = msg.content.strip("<@!>")
    else:
        user_id = mem.id

    if user_id == "everyone":
        embed = discord.Embed(
            title="You just tried to add everyone to this one ticket.",
            description="No.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return
    try:
        # Verifies the user is a real user
        user = await interaction.guild.fetch_member(int(user_id))
    except discord.NotFound:
        await interaction.followup.send(
            "Invalid user ID or mention.", ephemeral=True
        )
        return
    entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
    entry.involved_players_discord += f",{user_id}"
    entry.update()
    await channel.set_permissions(
        user, read_messages=True, send_messages=True
    )
    await interaction.followup.send(f"{user.mention} has been added to the ticket.")

async def create_channel_helper(interaction: discord.Interaction, ticket_id):
    print("Creating ticket!")
    sql_entry = sql.fetch_by_id(int(ticket_id))
    players = sql_entry.involved_players_discord.split(",")
    overwrites = {
    interaction.guild.default_role: discord.PermissionOverwrite(
        read_messages=False, send_messages=False
    ),
    interaction.user: discord.PermissionOverwrite(
        read_messages=True, send_messages=True
    )
    }
    pnames = []
    for player in players:
        #NOTE:
        # fetch_user is an api call and should be used sparingly
        # for whatever reason, get_user only reaches into the bot cache, which at the moment doesnt seem to contain member info
        # This also means that it can be used to find player data on players not in the server
        # So use with caution 
        player_discord = await bot.fetch_user(player)
        pnames.append(player_discord.mention)

        overwrites[player_discord] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True
        )

    tickets_category = discord.utils.get(interaction.guild.categories, name="Tickets")
    ticket_channel_name = f"ticket-{ticket_id}"
    ticket_channel = await interaction.guild.create_text_channel(
        ticket_channel_name, category=tickets_category, overwrites=overwrites
    )

    # Send a message in the new channel
    involved_players = ""
    for name in pnames:
        involved_players += f"{name}, "

    involved_players = involved_players[:len(involved_players)-2]
    embed = discord.Embed(
        title=f"Ticket #{ticket_id} information",
        description=f"Players involved: {involved_players}\nTicket Message: {sql_entry.message}",
        color=discord.Color.green()
    )
    view = discord.ui.View(timeout=None)
    view.add_item(DynamicButton(ticket_id=ticket_id, button_type="close"))
    view.add_item(DynamicButton(ticket_id=ticket_id, button_type="add"))
    msg = await ticket_channel.send(
        embed=embed, view=view
    )
    await msg.pin()

    # Reply to the user in the original channel
    await interaction.response.send_message(
        embed = discord.Embed(
            title="Channel Created Notification",
            description=f"{ticket_channel.mention} has been created!",
            color=discord.Color.blue(),
        ),
        ephemeral=True
    )

async def create_ticket_helper(interaction: discord.Interaction, info:dict):
    # Create a new channel named "ticket-{user_id}"
    try:
        ticket_id = int(sql.get_most_recent_entry(TABLE_NAME, only_id=True)) + 1
    except IndexError:
        ticket_id = 1
    staff_channel = discord.utils.get(interaction.guild.channels, name=OPEN_TICKET_CHANNEL)
    # Hardcoded Dict, can't think of a way to load this from a config file
    message = info["message"]
    server = info["server"]
    player_ign = info["ingame-name"]
    table_dict = {
        "id": ticket_id,
        "involved_players_discord": str(interaction.user.id),
        # TODO:
        # Add logic to look up player's ingame minecraft name, or vice versa
        "involved_players_minecraft": "",
        "involved_staff_discord": "",
        "involved_staff_minecraft": "",
        "status": "open",
        # TODO:
        # Update message field with info player fills in from UI
        "message": message,
    }

    # Create the ticket in sql
    ticket = sql.TableEntry(table_info=table_dict)

    # Push it!
    ticket.push()
    await interaction.response.send_message(
    embed=discord.Embed(
        title="Ticket Created!",
        description=f"Your ticket, ticket #{ticket_id}, has been created! A staff member will contact you shortly for the next steps.",
        color=discord.Color.green()
        ), 
    ephemeral=True, 
    delete_after=30
    )
    embed = discord.Embed(
        title=f"Ticket #{ticket_id}",
        description=
        f"""User: {interaction.user.mention}
        Discord ID: {interaction.user.id}
        Minecraft In-Game Name: {player_ign}
        Server: {server}
        Description: {message}""",
        color=discord.Color.green()
    )
    view = discord.ui.View()
    view.add_item(DynamicButton(ticket_id=ticket_id, button_type="claim", button_style=discord.ButtonStyle.green))

    await staff_channel.send(embed=embed, view=view)

async def claim_ticket_helper(interaction: discord.Interaction, ticket_num=None, view=None):
    # Check if in ticket channel
    # Check role, ex staff
    # TODO:
    # Move role checks to dynamic button interaction_check func
    # https://discordpy.readthedocs.io/en/latest/interactions/api.html#discord.ui.DynamicItem.interaction_check
    ticket_id = ticket_num
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE)
    if staff_role and staff_role in interaction.user.roles:
        if not ticket_id:
            # Grab ticket ID from the channel name
            try:
                ticket_id = int(interaction.channel.name.split("-")[1])
            except ValueError:
                print(
                    f"WARNING!!!!! TICKET {interaction.channel.name} HAS INVALID TITLE!!"
                )
                await interaction.response.send_message(
                    embed = discord.Embed(
                        title="Error",
                        description="I'm sorry, I cannot close the ticket as I cannot find the ID. Please report this error.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
        else:
            try:
                ticket_id = int(ticket_id)
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Ticket ID",
                    description=f"Ticket ID {ticket_id} is not a valid ID. Please retry with a valid ID.",
                    color= discord.Color.blue(),
                )
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                    )
                return
        staff_member = interaction.user.id
        # Update database logic here
        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        if len(entry.involved_staff_discord) > 0:
            staff_name = bot.get_user(staff_member).name
            await interaction.response.send_message(
                embed = discord.Embed(
                title="Ticket Claim Error",
                description=f"Ticket #{ticket_id} has already been claimed by {staff_name}.",
                color=discord.Color.yellow()
                ),
                ephemeral=True
            )
            return
        entry.involved_staff_discord = str(staff_member)
        entry.status = "claimed"
        entry.update_dict()
        entry.update()
        await interaction.message.delete()
        view = discord.ui.View()
        view.add_item(DynamicButton(ticket_id=ticket_id, button_type="close", button_style=discord.ButtonStyle.green))
        view.add_item(DynamicButton(ticket_id=ticket_id, button_type="channel", button_style=discord.ButtonStyle.blurple))
        await interaction.response.send_message(
            embed = discord.Embed(
                title=f"Ticket #{ticket_id} Claimed",
                description=f"Ticket #{ticket_id} has been claimed by {interaction.user.mention}.",
                color=discord.Color.green()
            ),
            ephemeral=False,
            view=view
        )
    else:
        # Non-staff reply
        await interaction.response.send_message(
            embed = discord.Embed(
                title="Claim Error: Role Not Found",
                description=f"You need the {STAFF_ROLE} role to claim a support ticket.",
                color=discord.Color.yellow()
            ),
            ephemeral=True
        )

async def close_ticket_helper(interaction: discord.Interaction, ticket_num=None):

    # Grab ticket ID from the channel name
    ticket_channel = discord.utils.get(interaction.guild.text_channels, name=f"ticket-{ticket_num}")
    if not ticket_num:
        try:
            ticket_id = int(interaction.channel.name.split("-")[1])
        except ValueError:
            print(f"WARNING!!!!! TICKET {interaction.channel.name} HAS INVALID TITLE!!")
            interaction.response.send_message(
                embed = discord.Embed(
                    title="Error",
                    description=f"I'm sorry, I cannot close the ticket as I cannot find the ID. Please report this error.",
                    color=discord.Color.red()
                )
            )
            return
    else:
        try:
            ticket_id = int(ticket_num)
        except ValueError:
            embed = discord.Embed(
                title="Error",
                description=f"Please enter a valid ticket ID.",
                color=discord.Color.red(),
                ephemeral=True,
            )
            interaction.response.send_message(embed=embed, ephemeral=True)
            return
    # Archive command here
    # await interaction.channel.delete()
    # Notify channel is closed, dont delete yet
    entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
    entry.status = "closed"
    if ticket_channel: 
        curr_overwrites = ticket_channel.overwrites
        keys = list(curr_overwrites.keys())
        print(keys)
        for key in keys[1:]:
            member = bot.get_user(int(key.id))
            await ticket_channel.set_permissions(
                member, send_messages=False, read_messages=True
            )
    entry.update_dict()
    entry.update()
    await interaction.response.send_message(
        embed = discord.Embed(
            title=f"Ticket #{ticket_id} closed",
            description=f"Ticket #{ticket_id} has been closed.",
            color=discord.Color.blue()
        )
    )

"""
===========================================================================
==================================BUTTONS==================================
===========================================================================
"""


"""
What are the button states?
1. Open
    Claim
2. Claimed
    Close
    Add user
3. Closed
    Re open (open)
    Chat is unusable

"""
class DynamicButton(discord.ui.DynamicItem[discord.ui.Button], template=r'button:(?P<type>[a-zA-Z]+):(?P<id>[0-9]+)'):
    def __init__(self, *, ticket_id, button_type:str, button_style:discord.ButtonStyle=discord.ButtonStyle.green) -> None:
        """
        Possible Button Types:

        channel: Creates a new text channel 
        add: Adds a new user to the channel <- TODO: Use discord.ui.Select for this
        close: Closes the associated ticket 
        reopen: Reopens ticket, currently not in use
        claim: Claims the associated ticket 
        open: Creates a new ticket
        
        """
        button_type = button_type.lower()
        


        if button_type == "channel":
            button_label = "Create a Text Channel"
            button_style = discord.ButtonStyle.blurple
        elif button_type == "add":
            button_label = "Add User"
        elif button_type == "close":
            button_label = "Close Ticket"
            button_style = discord.ButtonStyle.red
        elif button_type == "reopen":
            button_label = "Reopen Ticket"
        elif button_type == "claim":
            button_label = "Claim Ticket"
        elif button_type == "open":
            button_label = str("Open a Ticket \U0001F4E9")
            button_style = discord.ButtonStyle.gray
        else:
            button_label = "Undefined button_type!"

        super().__init__(
            item=discord.ui.Button(
                label=f"{button_label}",
                style=button_style,
                custom_id=f'button:{button_type}:{ticket_id}',
            )
        )
        self.id = ticket_id
        self.button_type = button_type

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /):
        id = str(match['id'])
        button_type = str(match['type']).lower()
        # This elif chain feels redundant
        # It's basically a copy/paste of the init function
        if button_type == "close":
            style = discord.ButtonStyle.red
        elif button_type == "channel":
            style = discord.ButtonStyle.blurple
        elif button_type == "open":
            style = discord.ButtonStyle.gray
            # This ID never gets used
            # create_ticket_helper gets its own ID when it's called
            # But if we call the constructor without an ID it gets fussy about not matching the template so
            try:
                id = str(sql.get_most_recent_entry(TABLE_NAME, True)+1)
            except IndexError:
                id = 1
        else:
            style = discord.ButtonStyle.green
        return cls(ticket_id=id, button_type=button_type, button_style=style)
        # await claim_ticket_helper(interaction)
    
    async def callback(self, interaction: discord.Interaction) -> None:
        #TODO: 
        # implement add button
        if self.button_type == "claim":
            await claim_ticket_helper(interaction, self.id)
        elif self.button_type == "channel":
            await create_channel_helper(interaction, self.id)
        elif self.button_type == "close":
            archive_category = discord.utils.get(interaction.guild.channels, name="ticket-archive")
            await interaction.channel.edit(name=f"{interaction.channel.name}-closed", category=archive_category)
            await close_ticket_helper(interaction, self.id)
        elif self.button_type == "open":
            modal = TicketModal()
            await interaction.response.send_modal(modal)
        elif self.button_type == "add":
            await add_user_helper(interaction, self.id)
        else:
            embed = discord.Embed(
                title = "Unexpected Error",
                description = f"An unexpected error has occured, and the button you have clicked is not a valid button. Please report this issue.\nButton Type: {self.button_type}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        

class ButtonOpen(discord.ui.View):
    """
    What does this button class do?
    This is attatched to messages where the ticket is in the state `Open`

    What does this add?
    Claim button
    """

    def __init__(self, *, timeout=None, custom_id=None):
        super().__init__(timeout=None)
        self.ticket_id = custom_id

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_button")
    async def claimButton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # https://stackoverflow.com/questions/74426018/attributeerror-button-object-has-no-attribute-response
        # We had a few attribute errors and this might be the right fix.
        await interaction.message.delete()
        await claim_ticket_helper(interaction, ticket_num=self.ticket_id, view=ButtonClaimed(custom_id=self.ticket_id))


class ButtonClaimed(discord.ui.View):
    """
    What does this button class do?
    This is attatched to messages where the ticket is in the state `Claim`

    What does this add?
    Close button
    Add staff button
    """

    def __init__(self, *, timeout=None, custom_id: int = None):
        super().__init__(timeout=None)
        self.ticket_id = custom_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_button")
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Logic for closing the ticket
        ticket_id = self.ticket_id

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        # Check if the user is the claiming staff member or an added staff member

        staff_id = entry.involved_staff_discord
        if str(interaction.user.id) != staff_id and str(interaction.user.id) not in entry.involved_players_discord.split(","):
            embed = discord.Embed(
                title="Unauthorized",
                description=f"You do not have permission to close this ticket.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        entry.status = "closed"
        entry.update()

        curr_overwrites = interaction.channel.overwrites
        keys = list(curr_overwrites.keys())
        for key in keys[1:]:
            member = interaction.guild.get_member(int(key.id))
            await interaction.channel.set_permissions(
                member, send_messages=False, read_messages=True
            )

        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Ticket #{ticket_id} has been closed.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, view=ButtonClosed(ticket_id=ticket_id))

    # TODO:
    # Move this button into the actual 
    @discord.ui.button(label="Add User", style=discord.ButtonStyle.green, custom_id="add_user")
    async def add_user_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket_channel = interaction.channel
        ticket_id = self.ticket_id

        def check(m):
            return m.channel == interaction.channel

        await interaction.response.send_message(
            "Please enter the user's ID or mention:", ephemeral=True
        )
        try:
            msg = await interaction.client.wait_for(
                "message", check=check, timeout=60.0
            )
            await msg.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Timed out waiting for user input.", ephemeral=True
            )
            return

        user_id = msg.content.strip("<@!>")
        try:
            # Verifies the user is a real user
            user = await interaction.guild.fetch_member(int(user_id))
        except discord.NotFound:
            await interaction.followup.send(
                "Invalid user ID or mention.", ephemeral=True
            )
            return

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        entry.involved_players_discord += f",{user_id}"
        entry.update()

        await ticket_channel.set_permissions(
            user, read_messages=True, send_messages=True
        )
        await interaction.followup.send(f"{user.mention} has been added to the ticket.")

    @discord.ui.button(label="Create Text Channel", style=discord.ButtonStyle.blurple, custom_id="create_channel")
    async def create_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_channel_helper(interaction, self.ticket_id)


class ButtonClosed(discord.ui.View):
    def __init__(self, *, timeout=None, custom_id: int = None):
        super().__init__(timeout=None)
        self.ticket_id = custom_id


    @discord.ui.button(label="Reopen Ticket", style=discord.ButtonStyle.green, custom_id="reopen_button")
    async def reopen_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket_id = self.ticket_id

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        entry.status = "open"
        entry.update()

        curr_overwrites = interaction.channel.overwrites
        keys = list(curr_overwrites.keys())
        for key in keys[1:]:
            member = interaction.guild.get_member(int(key.id))
            await interaction.channel.set_permissions(
                member, send_messages=True, read_messages=True
            )

        embed = discord.Embed(
            title="Ticket Reopened",
            description=f"Ticket #{ticket_id} has been reopened.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, view=ButtonClaimed(custom_id=ticket_id))

class ButtonTicket(discord.ui.View):
    """
    What does this button class do?
    This is attatched to messages where the ticket is in the state `Claim`

    What does this add?
    Close button
    Add staff button
    """

    def __init__(self, *, timeout=None, custom_id: int = None):
        super().__init__(timeout=None)
        self.ticket_id = custom_id


    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_button_claim")
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Logic for closing the ticket
        ticket_id = self.ticket_id

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        # Check if the user is the claiming staff member or an added staff member

        staff_id = entry.involved_staff_discord
        if str(interaction.user.id) != staff_id and str(interaction.user.id) not in entry.involved_players_discord.split(","):
            embed = discord.Embed(
                title="Unauthorized",
                description=f"You do not have permission to close this ticket.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        entry.status = "closed"
        entry.update()

        curr_overwrites = interaction.channel.overwrites
        keys = list(curr_overwrites.keys())
        for key in keys[1:]:
            member = interaction.guild.get_member(int(key.id))
            await interaction.channel.set_permissions(
                member, send_messages=False, read_messages=True
            )

        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Ticket #{ticket_id} has been closed.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, view=ButtonClosed(ticket_id=ticket_id))

    # TODO:
    # Move this button into the actual 
    @discord.ui.button(label="Add User", style=discord.ButtonStyle.green, custom_id="add_staff")
    async def add_user_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket_channel = interaction.channel
        ticket_id = self.ticket_id

        def check(m):
            return m.channel == interaction.channel

        await interaction.response.send_message(
            "Please enter the user's ID or mention:", ephemeral=True
        )
        try:
            msg = await interaction.client.wait_for(
                "message", check=check, timeout=60.0
            )
            await msg.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Timed out waiting for user input.", ephemeral=True
            )
            return

        user_id = msg.content.strip("<@!>")
        try:
            # Verifies the user is a real user
            user = await interaction.guild.fetch_member(int(user_id))
        except discord.NotFound:
            await interaction.followup.send(
                "Invalid user ID or mention.", ephemeral=True
            )
            return

        entry = sql.fetch_by_id(ticket_id, CONFIG_FILENAME)
        entry.involved_players_discord += f",{user_id}"
        entry.update()

        await ticket_channel.set_permissions(
            user, read_messages=True, send_messages=True
        )
        await interaction.followup.send(f"{user.mention} has been added to the ticket.")

class TicketOpen(discord.ui.View):
    """
    What does this button class do?
    This is attatched to messages where the ticket is in the state `Open`

    What does this add?
    Claim button
    """

    def __init__(self, *, timeout=None, custom_id=None):
        super().__init__(timeout=timeout)
        self.ticket_id = custom_id


    @discord.ui.button(label="Create a Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def claimButton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        #TODO:
        # Integrate GUI popup with this button
        await create_ticket_helper(interaction)
        embed = discord.Embed(
            title="Ticket Created!",
            description="A staff member will contact you shortly for further information.",
            color=discord.Color.green()
        )
        await interaction.channel.send(
            embed=embed
        )

class TicketModal(discord.ui.Modal, title='New Ticket Form'):
    """
    Small Modal class for the Open Ticket Button
    """
    ign = discord.ui.TextInput(label="In-Game Name:", placeholder="Enter your ingame name here (can be left blank)", required=False)
    server = discord.ui.TextInput(label="Server:", placeholder="Server the problem is ocurring on", required=True)
    message = discord.ui.TextInput(label="Tell us the problem:", placeholder="Describe the issue here for us.", max_length=4000, required=True, style=discord.TextStyle.long)

    async def on_submit(self, interaction:discord.Interaction):
        data = {
            "ingame-name": self.ign.value,
            "server": self.server.value,
            "message": self.message.value
                }
        await create_ticket_helper(interaction, info=data)


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = Bot(intents)
tree = app_commands.CommandTree(bot)


if __name__ == "__main__":
    pass