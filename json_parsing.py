import discord
import json
import sql_interface as sql


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
            # Parse the JSON data from the message content
            json_data = json.loads(message.content)

            # Extract the event type from the JSON data
            event = json_data.get("event")

            # Call the appropriate event handler based on the event type
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
        try:
            # Create a player object from the Discord ID
            player = sql.player_from_interaction(discord.Object(id=int(discord_id)))

            # Create a new ticket entry in the database
            entry = sql.TableEntry(
                players=str(player),
                staff="",
                message=message,
                status="open",
                table="players",
            )
            entry.push()

            # Get the ID of the newly created ticket
            ticket_id = sql.get_most_recent_entry("players", only_id=True)

            # Get the "Tickets" category
            category = discord.utils.get(self.guild.categories, name="Tickets")

            # Generate the channel name for the ticket
            channel_name = f"ticket-{ticket_id}"

            # Set the channel permissions
            overwrites = {
                self.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False
                ),
                discord_id: discord.PermissionOverwrite(read_messages=True),
            }

            # Create a new text channel for the ticket
            channel = await self.guild.create_text_channel(
                channel_name, category=category, overwrites=overwrites
            )

            # Create an embedded message with ticket details
            embed = discord.Embed(
                title=f"Ticket #{ticket_id}",
                description=message,
                color=discord.Color.blue(),
            )
            embed.add_field(name="Created by", value=f"<@{discord_id}>", inline=False)
            embed.add_field(name="Status", value="Open", inline=False)

            # Send the embedded message in the ticket channel
            await channel.send(embed=embed)
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
