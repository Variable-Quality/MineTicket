import discord
import json as pyjson
import sql_interface as sql
from configmanager import database_config_manager as db_cfm
from helpers import *

# Solomon/DJ - when you get to this point in the merge - We need the naming of the buttons to change into what they are *now* with the new stuff. THis was written for the old way of doing buttons.

CFM = db_cfm()
TABLE_NAME = CFM.cfg["DATABASE"]["table"]


class ParseJSON:
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild

    def setup_listener(self):
        # This section may not be necessary in a bit, we will see
        @self.client.event
        async def on_message(message):
            if (
                message.channel.name == "intake"
                and message.channel.category.name == "Tickets"
            ):
                await self.parse_json_message(message)

    async def parse_json_message(self, message):
        """
        Parses the JSON message and triggers the appropriate event handler based on the event type.

        Args:
            message (discord.Message): The message object containing the JSON data.

        Returns:
            None
        """
        try:
            json_data = pyjson.loads(message.content)
            event = json_data.get("event")

            if event == "create":
                user_uuid = json_data.get("user-uuid")
                discord_id = json_data.get("discord-id")
                message_content = json_data.get("message")
                await self.create_event(user_uuid, discord_id, message_content)
            elif event == "claim":
                ticket_id = json_data.get("id")
                user_uuid = json_data.get("user-uuid")
                discord_id = json_data.get("discord-id")
                await self.claim_event(ticket_id, user_uuid, discord_id)
            elif event == "close":
                ticket_id = json_data.get("id")
                user_uuid = json_data.get("user-uuid")
                discord_id = json_data.get("discord-id")
                message_content = json_data.get("message")
                await self.close_event(
                    ticket_id, user_uuid, discord_id, message_content
                )
            else:
                print(f"Unknown event type: {event}")
        except pyjson.JSONDecodeError:
            print(f"Invalid JSON format in message\n{message.content}")

    async def create_event(self, user_uuid, discord_id, message):
        """
        Creates a new ticket based on the provided user UUID, Discord ID, and message.

        Args:
            user_uuid (str): The UUID of the user creating the ticket.
            discord_id (str): The Discord ID of the user creating the ticket.
            message (str): The message content of the ticket.

        Returns:
            None
        """
        try:
            user = self.bot.get_user(int(discord_id))

            if user is None:
                raise ValueError(f"User with ID {discord_id} not found.")

            player = sql.Player(user.name, discord_id)

            # Create a new ticket entry using the table configuration from configmanager
            table_dict = {
                "id": None,
                "involved_players_discord": str(player),
                "involved_players_minecraft": "",
                "involved_staff_discord": "",
                "involved_staff_minecraft": "",
                "status": "open",
                "message": message,
            }

            entry = sql.TableEntry(table_info=table_dict)
            entry.push()

            ticket_id = sql.get_most_recent_entry(TABLE_NAME, only_id=True)

            mineticket_feed_channel = discord.utils.get(
                self.guild.text_channels, name="mineticket-feed"
            )

            if mineticket_feed_channel is None:
                raise ValueError("Mineticket Feed channel not found.")

            embed = discord.Embed(
                title=f"Ticket #{ticket_id}",
                description=message,
                color=discord.Color.blue(),
            )
            embed.add_field(name="Created by", value=user.mention, inline=False)
            embed.add_field(name="Status", value="Open", inline=False)

            buttons = ButtonOpen(custom_id=ticket_id)
            await mineticket_feed_channel.send(embed=embed, view=buttons)
        except Exception as e:
            print(f"Error creating ticket: {str(e)}")

    async def claim_event(self, ticket_id, user_uuid, discord_id):
        """
        Claims a ticket by updating the ticket status and assigning the staff member.

        Args:
            ticket_id (int): The ID of the ticket to be claimed.
            user_uuid (str): The UUID of the user claiming the ticket.
            discord_id (str): The Discord ID of the user claiming the ticket.

        Returns:
            None
        """
        # Update the ticket status to "claimed" and assign the staff member
        entry = sql.fetch_by_id(ticket_id, TABLE_NAME)
        if entry:
            staff_member = sql.player_from_interaction(
                discord.Object(id=int(discord_id))
            )
            entry.involved_staff_discord = str(staff_member)
            entry.status = "claimed"
            entry.update()

    async def close_event(self, ticket_id, user_uuid, discord_id, message):
        """
        Closes a ticket by updating the ticket status and message.

        Args:
            ticket_id (int): The ID of the ticket to be closed.
            user_uuid (str): The UUID of the user closing the ticket.
            discord_id (str): The Discord ID of the user closing the ticket.
            message (str): The closing message for the ticket.

        Returns:
            None
        """
        # Close the ticket and update the message
        entry = sql.fetch_by_id(ticket_id, TABLE_NAME)
        if entry:
            entry.status = "closed"
            entry.message = message
            entry.update()
