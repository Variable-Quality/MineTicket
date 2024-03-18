import discord
from discord import app_commands
from discord.ext import commands
import sql_interface as sql
import random
import ui


# main source - https://gist.github.com/lykn/bac99b06d45ff8eed34c2220d86b6bf4
class Buttons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

    """
    1 - open ticket
    2 - claim ticket
    3 - close ticket
    
    if userRole in config.rolesList # ['1', '2']
    """

    @discord.ui.button(label="openButton", style=discord.ButtonStyle.gray)
    async def openButton(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.channel.send_modal(ui.ticket_ui_create())

    @discord.ui.button(label="claimButton", style=discord.ButtonStyle.green)
    async def claimButton(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.response.send_modal(ui.ticket_ui_claim())

    @discord.ui.button(label="closeButton", style=discord.ButtonStyle.red)
    async def closeButton(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        staff = sql.player_from_interaction(interaction)
        sql_entry = sql.TableEntry(
            str(players),
            str(staff),
            staff_member,
            self.status.value,
            "claim",
            TABLE_NAME,
            int(ticket_num.value),
        )
        sql_entry.update()
        await interaction.response.send_message(content="Ticket closed")
