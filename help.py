import discord
from discord.ext import commands

@discord.hybrid_command(name='help', description='Shows available commands and their descriptions')
async def help_command(interaction: discord.Interaction):
    # Create an embed for the help message
    embed = discord.Embed(title="Help", description="List of main commands:")

    # Add descriptions for the main commands
    main_commands = {
        "create_ticket": "Creates a new ticket.",
        "claim_ticket": "Claims an existing ticket.",
        "close_ticket": "Closes a ticket."
    }

    for command_name, description in main_commands.items():
        embed.add_field(name=command_name, value=description, inline=False)

    # Send the embed as a direct message to the user
    await interaction.author.send(embed=embed)

    # Respond to the user in the current channel
    await interaction.response.send_message("Help message sent to your DMs!", ephemeral=True)