import discord
from discord import ui
from helpers import *


class PersistentViews(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket"
    )
    async def open_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(TicketOpen())

    @discord.ui.button(
        label="Claim Ticket",
        style=discord.ButtonStyle.blurple,
        custom_id="claim_ticket",
    )
    async def claim_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket_id = int(interaction.message.embeds[0].title.split("#")[1])
        await interaction.response.edit_message(view=ButtonClaimed(custom_id=ticket_id))

    @discord.ui.button(
        label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket"
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket_id = int(interaction.message.embeds[0].title.split("#")[1])
        await interaction.response.edit_message(view=ButtonClosed(ticket_id=ticket_id))
