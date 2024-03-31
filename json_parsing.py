import discord
import json
import sql_interface as sql


class ParseJSON:
    def __init__(self, client, guild):
        self.client = client
        self.guild = guild
        self.setup_listener()

    def setup_listener(self):
        @self.client.event
        async def on_message(message):
            if (
                message.channel.name == "intake"
                and message.channel.category.name == "Tickets"
            ):
                await self.parse_json_message(message)

    async def parse_json_message(self, message):
        try:
            json_data = json.loads(message.content)
            # Extract relevant information from JSON data
            event = json_data.get("event")
            user_uuid = json_data.get("user-uuid")
            discord_id = json_data.get("discord-id")
            message_content = json_data.get("message")
            # Call the corresponding event handler based on the event type
            if event == "create":
                await self.create_event(user_uuid, discord_id, message_content)
            elif event == "claim":
                ticket_id = json_data.get("id")
                await self.claim_event(ticket_id, user_uuid, discord_id)
            elif event == "close":
                ticket_id = json_data.get("id")
                await self.close_event(
                    ticket_id, user_uuid, discord_id, message_content
                )
        except json.JSONDecodeError:
            print("Invalid JSON format")

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
        # Create a ticket in the database
        player = sql.player_from_interaction(discord.Object(id=int(discord_id)))
        entry = sql.TableEntry(
            players=str(player),
            staff="",
            message=message,
            status="open",
            table="players",
        )
        entry.push()
        ticket_id = sql.get_most_recent_entry("players", only_id=True)

        # Create a separate channel for the ticket
        category = discord.utils.get(self.guild.categories, name="Tickets")
        channel_name = f"ticket-{ticket_id}"
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            discord_id: discord.PermissionOverwrite(read_messages=True),
        }
        channel = await self.guild.create_text_channel(
            channel_name, category=category, overwrites=overwrites
        )

        # Send an embedded message in the ticket channel
        embed = discord.Embed(
            title=f"Ticket #{ticket_id}",
            description=message,
            color=discord.Color.blue(),
        )
        # TODO: Add buttons for claiming and closing the ticket
        await channel.send(embed=embed)

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
        entry = sql.fetch_by_id(ticket_id, "players")
        if entry:
            staff_member = sql.player_from_interaction(
                discord.Object(id=int(discord_id))
            )
            entry.involved_staff = str(staff_member)
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
        entry = sql.fetch_by_id(ticket_id, "players")
        if entry:
            entry.status = "closed"
            entry.message = message
            entry.update()
