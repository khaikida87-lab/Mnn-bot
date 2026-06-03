import discord
from discord import app_commands
from discord.ext import commands
import asyncio

CATEGORY_NAME = "📩┃REQUESTS"

class StaffRequestButton(discord.ui.View):
    def __init__(self, button_label: str):
        super().__init__(timeout=None)
        self.add_item(HantarRequestButton(label=button_label))

class HantarRequestButton(discord.ui.Button):
    def __init__(self, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.blurple, emoji="📩", custom_id="hantar_request_persistent")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if not category:
            try:
                category = await guild.create_category(CATEGORY_NAME)
                await category.set_permissions(guild.default_role, read_messages=False)
            except discord.Forbidden:
                return await interaction.followup.send("Bot takde permission `Manage Channels` untuk buat category.", ephemeral=True)
        
        existing = discord.utils.get(guild.text_channels, topic=f"Request dari {interaction.user.id}")
        if existing:
            return await interaction.followup.send(f"Kau dah ada ticket aktif: {existing.mention}", ephemeral=True)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        channel = await guild.create_text_channel(
            name=f"request-{interaction.user.name}"[:50],
            category=category,
            overwrites=overwrites,
            topic=f"Request dari {interaction.user.id}"
        )
        
        embed = discord.Embed(
            title="📩 Staff Request Baru",
            description=f"Request dari {interaction.user.mention}\n\nSila taip detail request kau kat sini. Staff akan review secepat mungkin.",
            color=0x3498db
        )
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        
        await channel.send(content="@here", embed=embed, view=AcceptRejectButtons(interaction.user))
        await interaction.followup.send(f"Ticket request dah dibuat: {channel.mention}", ephemeral=True)

class AcceptRejectButtons(discord.ui.View):
    def __init__(self, requester: discord.Member):
        super().__init__(timeout=None)
        self.requester = requester
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅", custom_id="req_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Kau bukan admin", ephemeral=True)
        await interaction.response.edit_message(embed=discord.Embed(title="✅ Request Accepted", color=0x00ff00, description=f"Diterima oleh {interaction.user.mention}"), view=None)
        await interaction.channel.send(f"{self.requester.mention} request kau dah accept!")

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, emoji="❌", custom_id="req_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Kau bukan admin", ephemeral=True)
        await interaction.response.edit_message(embed=discord.Embed(title="❌ Request Rejected", color=0xff0000, description=f"Ditolak oleh {interaction.user.mention}"), view=None)
        await interaction.channel.send(f"{self.requester.mention} request kau kena reject.")
        
    @discord.ui.button(label="Close", style=discord.ButtonStyle.grey, emoji="🔒", custom_id="req_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Kau bukan admin", ephemeral=True)
        await interaction.response.send_message("Channel akan delete dalam 5 saat...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class RequestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(StaffRequestButton("Hantar request")) 
        self.bot.add_view(AcceptRejectButtons(None))

    @app_commands.command(name="request", description="Hantar butang untuk member buat request")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        text_button="Teks untuk button",
        description="Description kat embed"
    )
    async def request(self, interaction: discord.Interaction, text_button: str = "Hantar request", description: str = "Tekan button bawah untuk buat ticket request staff"):
        embed = discord.Embed(
            title="📩 Staff Request",
            description=description,
            color=0x5865f2
        )
        await interaction.response.send_message(embed=embed, view=StaffRequestButton(text_button))

async def setup(bot):
    await bot.add_cog(RequestCog(bot))
