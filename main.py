from threading import Thread 
from flask import Flask
import os

app = Flask('')

@app.route('/')
def home():
    return "OK"

def run():
  app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# --- Code bot kau start kat bawah ni ---
import discord
from discord.ext import commands
from discord import app_commands
import os

db = {}  # WAJIB ADA LINE NIe
TOKEN = os.environ.get("DISCORD_TOKEN")
OWNER_ID = 0  # Will be fetched dynamically via @khaikida87 username search

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
@bot.event
async def setup_hook():
    await bot.load_extension("cogs.request")

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)


# ─── Helpers ────────────────────────────────────────────────────────────────

def is_approved(guild_id: int) -> bool:
    return db.get(f"approved_{guild_id}") == True


def approval_error():
    embed = discord.Embed(
        title="❌ Tiada Permission",
        description="Server ni takde permission. Guna `/permission` dulu untuk mohon akses.",
        color=discord.Color.red()
    )
    return embed


def is_admin(member: discord.Member) -> bool:
    return member.guild_permissions.administrator


def has_manage_messages(member: discord.Member) -> bool:
    return member.guild_permissions.manage_messages


async def get_owner(guild: discord.Guild) -> discord.Member | None:
    """Find owner by username khaikida87"""
    async for member in guild.fetch_members(limit=None):
        if member.name == "khaikida87":
            return member
    return None


async def get_role(guild: discord.Guild, key: str) -> discord.Role | None:
    role_id = db.get(key)
    if role_id:
        return guild.get_role(int(role_id))
    return None


async def add_server_to_db(guild_id: int):
    db[f"approved_{guild_id}"] = True


# ─── Views / UI Components ──────────────────────────────────────────────────

class VerifyModal(discord.ui.Modal, title="Verify Diri"):
    roblox_username = discord.ui.TextInput(
        label="Username Roblox",
        placeholder="Masukkan username Roblox anda...",
        min_length=3,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        owner = interaction.guild.owner
        if owner is None:
            owner = await interaction.guild.fetch_member(interaction.guild.owner_id)

        if owner is None:
            await interaction.response.send_message("❌ Owner tak jumpa. Pastikan Server Members Intent ON", ephemeral=True)
            return

        await owner.send("Ada orang nak verify")

        embed = discord.Embed(
            title="📋 Permohonan Verify Baru",
            color=discord.Color.orange()
        )
        embed.add_field(name="Discord User", value=f"{interaction.user.mention} (`{interaction.user}`)", inline=False)
        embed.add_field(name="Discord ID", value=str(interaction.user.id), inline=True)
        embed.add_field(name="Roblox Username", value=self.roblox_username.value, inline=True)
        embed.add_field(name="Server", value=f"{interaction.guild.name} (`{interaction.guild.id}`)", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        view = VerifyApproveRejectView(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            roblox_username=self.roblox_username.value
        )

        try:
            await owner.send(embed=embed, view=view)
            await interaction.response.send_message(
                "✅ Permohonan verify anda telah dihantar kepada owner. Tunggu kelulusan!", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Gagal hantar DM kepada owner. Hubungi admin.", ephemeral=True
            )


class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify Diri", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())


class VerifyApproveRejectView(discord.ui.View):
    def __init__(self, user_id: int, guild_id: int, roblox_username: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.guild_id = guild_id
        self.roblox_username = roblox_username

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = bot.get_guild(self.guild_id)
        if not guild:
            await interaction.response.send_message("❌ Server tidak dijumpai.", ephemeral=True)
            return

        member = guild.get_member(self.user_id)
        if not member:
            await interaction.response.send_message("❌ User tidak dijumpai dalam server.", ephemeral=True)
            return

        role = await get_role(guild, f"role_verify_{self.guild_id}")
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

        try:
            await member.send(
                f"✅ Permohonan verify anda telah **diluluskan**!\n"
                f"Roblox Username: `{self.roblox_username}`\n"
                f"Role verify telah diberikan."
            )
        except discord.Forbidden:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Status", value="✅ APPROVED", inline=False)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = bot.get_guild(self.guild_id)
        member = guild.get_member(self.user_id) if guild else None

        try:
            if member:
                await member.send(
                    f"❌ Permohonan verify anda telah **ditolak**.\n"
                    f"Hubungi admin untuk maklumat lanjut."
                )
        except discord.Forbidden:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value="❌ REJECTED", inline=False)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


class PermissionApproveRejectView(discord.ui.View):
    def __init__(self, req_user_id: int, req_guild_id: int, req_guild_name: str):
        super().__init__(timeout=None)
        self.req_user_id = req_user_id
        self.req_guild_id = req_guild_id
        self.req_guild_name = req_guild_name

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        db[f"user_approved_{self.req_guild_id}_{self.req_user_id}"] = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Status", value="✅ ACCEPTED", inline=False)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

        try:
            req_user = await bot.fetch_user(self.req_user_id)
            await req_user.send("Permission diterima. Kau dah boleh guna bot ni ✅")
        except discord.Forbidden:
            pass

    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value="❌ REJECTED", inline=False)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

        try:
            req_user = await bot.fetch_user(self.req_user_id)
            await req_user.send("Permission ditolak oleh owner ❌")
        except discord.Forbidden:
            pass


class StaffRequestView(discord.ui.View):
    def __init__(self, channel_id: int, user_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.user_id = user_id
        self.guild_id = guild_id

    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.red, custom_id="staff_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.send("✅ Tiket ditutup. Channel akan dipadam dalam 5 saat...")
            import asyncio
            await asyncio.sleep(5)
            await channel.delete()
        await interaction.response.defer()

    @discord.ui.button(label="📝 Close with Reason", style=discord.ButtonStyle.grey, custom_id="staff_close_reason")
    async def close_with_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CloseReasonModal(channel_id=self.channel_id))


class CloseReasonModal(discord.ui.Modal, title="Sebab Penutupan"):
    reason = discord.ui.TextInput(
        label="Sebab",
        placeholder="Masukkan sebab penutupan tiket...",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            embed = discord.Embed(
                title="🔒 Tiket Ditutup",
                description=f"**Sebab:** {self.reason.value}",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            import asyncio
            await asyncio.sleep(5)
            await channel.delete()
        await interaction.response.defer()


class StaffRequestButton(discord.ui.View):
    def __init__(self, category_id: int | None, guild_id: int):
        super().__init__(timeout=None)
        self.category_id = category_id
        self.guild_id = guild_id

    @discord.ui.button(label="📩 Staff Request", style=discord.ButtonStyle.blurple, custom_id="staff_request_button")
    async def staff_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = guild.get_channel(self.category_id) if self.category_id else None

        tester_role = await get_role(guild, f"role_tester_{guild.id}")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if tester_role:
            overwrites[tester_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel_name = f"request-{interaction.user.name}"
        new_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📩 Staff Request Baru",
            description=f"Request dari {interaction.user.mention}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="User", value=f"{interaction.user} (`{interaction.user.id}`)")

        view = StaffRequestView(channel_id=new_channel.id, user_id=interaction.user.id, guild_id=guild.id)
        await new_channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"✅ Channel request anda dibuat: {new_channel.mention}", ephemeral=True
        )


# ─── Commands ───────────────────────────────────────────────────────────────

@tree.command(name="newschannel", description="Set channel untuk /news [Admin Only]")
@app_commands.describe(channel="Channel untuk berita")
async def newschannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Hanya admin boleh guna command ini.", ephemeral=True)
        return

    db[f"newschannel_{interaction.guild.id}"] = channel.id
    embed = discord.Embed(
        title="✅ News Channel Ditetapkan",
        description=f"Berita akan dihantar ke {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="news", description="Hantar berita ke news channel [Role News sahaja]")
@app_commands.describe(tajuk="Tajuk berita", berita="Kandungan berita", gambar="Upload gambar (optional)", video="Upload video (optional)")
async def news(interaction: discord.Interaction, tajuk: str, berita: str, gambar: discord.Attachment = None, video: discord.Attachment = None):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    news_role = await get_role(interaction.guild, f"role_news_{interaction.guild.id}")
    if news_role and news_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Hanya role **News** boleh guna command ini.", ephemeral=True)
        return

    channel_id = db.get(f"newschannel_{interaction.guild.id}")
    if not channel_id:
        await interaction.response.send_message("❌ News channel belum ditetapkan. Guna `/newschannel` dulu.", ephemeral=True)
        return

    news_channel = interaction.guild.get_channel(int(channel_id))
    if not news_channel:
        await interaction.response.send_message("❌ News channel tidak dijumpai.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"📰 {tajuk}",
        description=berita,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Dihantar oleh {interaction.user}", icon_url=interaction.user.display_avatar.url)

    if gambar:
        embed.set_image(url=gambar.url)

    await news_channel.send(embed=embed)

    if video:
        await news_channel.send(f"🎥 **Video:**", file=await video.to_file())

    await interaction.response.send_message(f"✅ Berita dihantar ke {news_channel.mention}!", ephemeral=True)


@tree.command(name="verified", description="Hantar butang verify diri")
async def verified(interaction: discord.Interaction):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    embed = discord.Embed(
        title="🔐 Verify Diri",
        description="Tekan butang di bawah untuk verify akaun Roblox anda.",
        color=discord.Color.gold()
    )
    view = VerifyButton()
    await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="manage", description="Set role untuk server [Admin Only]")
async def manage(interaction: discord.Interaction):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Hanya admin boleh guna command ini.", ephemeral=True)
        return

    view = ManageRoleView(guild=interaction.guild)
    embed = discord.Embed(
        title="⚙️ Manage Roles",
        description="Pilih role yang ingin ditetapkan:",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ManageRoleView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=120)
        self.guild = guild
        self.add_item(ManageRoleSelect(guild=guild))


class ManageRoleSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        options = [
            discord.SelectOption(label="Role Verify", value="role_verify", emoji="✅", description="Role yang diberi selepas verify"),
            discord.SelectOption(label="Role Tester", value="role_tester", emoji="🔧", description="Role untuk staff/tester"),
            discord.SelectOption(label="Role News", value="role_news", emoji="📰", description="Role untuk hantar berita"),
        ]
        super().__init__(placeholder="Pilih jenis role...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        label_map = {
            "role_verify": "Role Verify",
            "role_tester": "Role Tester",
            "role_news": "Role News"
        }
        view = RolePickerView(guild=self.guild, role_key=selected, label=label_map[selected])
        embed = discord.Embed(
            title=f"⚙️ Set {label_map[selected]}",
            description=f"Pilih role untuk dijadikan **{label_map[selected]}**:",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)


class RolePickerView(discord.ui.View):
    def __init__(self, guild: discord.Guild, role_key: str, label: str):
        super().__init__(timeout=120)
        self.add_item(RolePickerSelect(guild=guild, role_key=role_key, label=label))


class RolePickerSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, role_key: str, label: str):
        self.guild = guild
        self.role_key = role_key
        self.label_name = label
        options = [
            discord.SelectOption(label=role.name[:100], value=str(role.id))
            for role in guild.roles
            if not role.is_default() and not role.managed
        ][:25]
        if not options:
            options = [discord.SelectOption(label="Tiada role", value="none")]
        super().__init__(placeholder=f"Pilih {label}...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Tiada role tersedia.", ephemeral=True)
            return
        db[f"{self.role_key}_{self.guild.id}"] = int(self.values[0])
        role = self.guild.get_role(int(self.values[0]))
        embed = discord.Embed(
            title="✅ Role Ditetapkan",
            description=f"**{self.label_name}** ditetapkan kepada {role.mention}",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)


@tree.command(name="permission", description="Request access untuk guna bot dalam server ni")
async def permission(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user

    if interaction.user == interaction.guild.owner:
        await add_server_to_db(interaction.guild.id)
        await interaction.response.send_message("Kau owner kot 😂 Server auto approve", ephemeral=True)
        return

    if db.get(f"user_approved_{guild.id}_{user.id}"):
        await interaction.response.send_message("Kau dah ada permission bro", ephemeral=True)
        return

    owner = guild.owner
    if not owner:
        try:
            owner = await guild.fetch_member(guild.owner_id)
        except Exception:
            await interaction.response.send_message(
                "❌ Gagal jumpa owner server.", ephemeral=True
            )
            return

    embed = discord.Embed(
        title="📩 Request Access Bot",
        description=f"**{user.name}** nak guna bot/app dalam server **{guild.name}**",
        color=discord.Color.orange()
    )
    embed.add_field(name="User", value=f"{user.mention} (`{user}` / ID: `{user.id}`)", inline=False)
    embed.add_field(name="Server", value=f"{guild.name} (`{guild.id}`)", inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)

    view = PermissionApproveRejectView(
        req_user_id=user.id,
        req_guild_id=guild.id,
        req_guild_name=guild.name
    )

    try:
        await owner.send(embed=embed, view=view)
        await interaction.response.send_message(
            "✅ Request dah dihantar kat owner. Tunggu kejap!", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Gagal hantar DM kat owner. Mungkin DM dia tutup.", ephemeral=True
        )


@tree.command(name="lock", description="Lock channel semasa [Admin Only]")
async def lock(interaction: discord.Interaction):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Hanya admin boleh guna command ini.", ephemeral=True)
        return

    channel = interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=False)
    embed = discord.Embed(
        title="🔒 Channel Dikunci",
        description=f"{channel.mention} telah dikunci.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="unlock", description="Unlock channel semasa [Admin Only]")
async def unlock(interaction: discord.Interaction):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Hanya admin boleh guna command ini.", ephemeral=True)
        return

    channel = interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=None)
    embed = discord.Embed(
        title="🔓 Channel Dibuka",
        description=f"{channel.mention} telah dibuka semula.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="clear", description="Padam mesej [Perlukan 'Manage Messages']")
@app_commands.describe(jumlah="Bilangan mesej (1-100) atau 'all'")
async def clear(interaction: discord.Interaction, jumlah: str):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return
    if not has_manage_messages(interaction.user):
        await interaction.response.send_message("❌ Anda perlu permission **Manage Messages**.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    if jumlah.lower() == "all":
        deleted = await interaction.channel.purge(limit=None)
        await interaction.followup.send(f"✅ {len(deleted)} mesej telah dipadam.", ephemeral=True)
    else:
        try:
            amount = int(jumlah)
            if not 1 <= amount <= 100:
                await interaction.followup.send("❌ Masukkan nombor antara 1-100 atau 'all'.", ephemeral=True)
                return
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"✅ {len(deleted)} mesej telah dipadam.", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ Masukkan nombor antara 1-100 atau 'all'.", ephemeral=True)


@tree.command(name="request", description="Hantar butang Staff Request")
async def request(interaction: discord.Interaction):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    category_id = db.get(f"request_category_{interaction.guild.id}")
    embed = discord.Embed(
        title="📩 Staff Request",
        description="Tekan butang di bawah untuk buat request kepada staff.",
        color=discord.Color.blurple()
    )
    view = StaffRequestButton(
        category_id=int(category_id) if category_id else None,
        guild_id=interaction.guild.id
    )
    await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="ban", description="Ban pengguna [Role Tester+]")
@app_commands.describe(user="Pengguna untuk diban", reason="Sebab ban")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "Tiada sebab diberikan"):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    tester_role = await get_role(interaction.guild, f"role_tester_{interaction.guild.id}")
    if not is_admin(interaction.user):
        if not tester_role or tester_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Anda perlu role **Tester** atau lebih tinggi.", ephemeral=True)
            return

    if user.top_role >= interaction.user.top_role and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Anda tidak boleh ban user yang rank sama atau lebih tinggi.", ephemeral=True)
        return

    try:
        await user.send(f"🔨 Anda telah diban dari **{interaction.guild.name}**.\n**Sebab:** {reason}")
    except discord.Forbidden:
        pass

    await interaction.guild.ban(user, reason=reason)
    embed = discord.Embed(
        title="🔨 Ban",
        color=discord.Color.dark_red()
    )
    embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=True)
    embed.add_field(name="Oleh", value=interaction.user.mention, inline=True)
    embed.add_field(name="Sebab", value=reason, inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="kick", description="Kick pengguna [Role Tester+]")
@app_commands.describe(user="Pengguna untuk dikick", reason="Sebab kick")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "Tiada sebab diberikan"):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    tester_role = await get_role(interaction.guild, f"role_tester_{interaction.guild.id}")
    if not is_admin(interaction.user):
        if not tester_role or tester_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Anda perlu role **Tester** atau lebih tinggi.", ephemeral=True)
            return

    if user.top_role >= interaction.user.top_role and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Anda tidak boleh kick user yang rank sama atau lebih tinggi.", ephemeral=True)
        return

    try:
        await user.send(f"👢 Anda telah dikick dari **{interaction.guild.name}**.\n**Sebab:** {reason}")
    except discord.Forbidden:
        pass

    await interaction.guild.kick(user, reason=reason)
    embed = discord.Embed(
        title="👢 Kick",
        color=discord.Color.orange()
    )
    embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=True)
    embed.add_field(name="Oleh", value=interaction.user.mention, inline=True)
    embed.add_field(name="Sebab", value=reason, inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="mute", description="Timeout user untuk tempoh tertentu [Role Tester+]")
@app_commands.describe(user="User yang nak di-mute", duration="Tempoh (contoh: 10m, 2h, 1d)", reason="Sebab mute")
async def mute(interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "Tiada sebab diberikan"):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    tester_role = await get_role(interaction.guild, f"role_tester_{interaction.guild.id}")
    if not is_admin(interaction.user):
        if not tester_role or tester_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Anda perlu role **Tester** atau lebih tinggi.", ephemeral=True)
            return

    if user.bot:
        await interaction.response.send_message("❌ Tak boleh mute bot.", ephemeral=True)
        return

    if user.top_role >= interaction.user.top_role and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tak boleh mute user yang rank sama atau lebih tinggi.", ephemeral=True)
        return

    import re
    from datetime import timedelta, timezone, datetime as dt

    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    match = re.fullmatch(r"(\d+)([smhd])", duration.strip().lower())
    if not match:
        await interaction.response.send_message("❌ Format tempoh salah. Guna contoh: `10m`, `2h`, `1d`, `30s`", ephemeral=True)
        return

    amount, unit = int(match.group(1)), match.group(2)
    seconds = amount * units[unit]

    if seconds < 1 or seconds > 2419200:
        await interaction.response.send_message("❌ Tempoh mesti antara 1 saat hingga 28 hari.", ephemeral=True)
        return

    until = discord.utils.utcnow() + timedelta(seconds=seconds)

    try:
        await user.timeout(until, reason=reason)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot tak ada permission untuk timeout user ni.", ephemeral=True)
        return

    label_map = {"s": "saat", "m": "minit", "h": "jam", "d": "hari"}
    duration_label = f"{amount} {label_map[unit]}"

    try:
        await user.send(
            f"🔇 Kau telah di-mute dalam server **{interaction.guild.name}** selama **{duration_label}**.\n"
            f"**Sebab:** {reason}"
        )
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="🔇 Mute", color=discord.Color.dark_grey())
    embed.add_field(name="User", value=f"{user.mention} (`{user}`)", inline=True)
    embed.add_field(name="Oleh", value=interaction.user.mention, inline=True)
    embed.add_field(name="Tempoh", value=duration_label, inline=True)
    embed.add_field(name="Sebab", value=reason, inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@tree.command(name="unmute", description="Buang timeout user [Role Tester+]")
@app_commands.describe(user="User yang nak di-unmute")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    tester_role = await get_role(interaction.guild, f"role_tester_{interaction.guild.id}")
    if not is_admin(interaction.user):
        if not tester_role or tester_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Anda perlu role **Tester** atau lebih tinggi.", ephemeral=True)
            return

    if not user.is_timed_out():
        await interaction.response.send_message(f"✅ **{user}** tak kena mute pun.", ephemeral=True)
        return

    try:
        await user.timeout(None, reason=f"Unmute oleh {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot tak ada permission untuk unmute user ni.", ephemeral=True)
        return

    try:
        await user.send(f"🔊 Kau telah di-unmute dalam server **{interaction.guild.name}**.")
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="🔊 Unmute", color=discord.Color.green())
    embed.add_field(name="User", value=f"{user.mention} (`{user}`)", inline=True)
    embed.add_field(name="Oleh", value=interaction.user.mention, inline=True)
    embed.set_thumbnail(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@tree.command(name="warn", description="Bagi amaran kepada user [Role Tester+]")
@app_commands.describe(user="User yang nak diwarn", reason="Sebab amaran")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    tester_role = await get_role(interaction.guild, f"role_tester_{interaction.guild.id}")
    if not is_admin(interaction.user):
        if not tester_role or tester_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Anda perlu role **Tester** atau lebih tinggi.", ephemeral=True)
            return

    if user.bot:
        await interaction.response.send_message("❌ Tak boleh warn bot.", ephemeral=True)
        return

    key = f"warnings_{interaction.guild.id}_{user.id}"
    warnings = list(db.get(key) or [])
    warnings.append({
        "reason": reason,
        "by": str(interaction.user),
        "by_id": interaction.user.id,
        "timestamp": discord.utils.utcnow().isoformat()
    })
    db[key] = warnings

    try:
        await user.send(
            f"⚠️ Kau dapat warning dalam server **{interaction.guild.name}**!\n"
            f"**Sebab:** {reason}\n"
            f"**Total warning:** {len(warnings)}"
        )
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="⚠️ Warning", color=discord.Color.yellow())
    embed.add_field(name="User", value=f"{user.mention} (`{user}`)", inline=True)
    embed.add_field(name="Oleh", value=interaction.user.mention, inline=True)
    embed.add_field(name="Sebab", value=reason, inline=False)
    embed.add_field(name="Total Warning", value=f"**{len(warnings)}** kali", inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@tree.command(name="warnings", description="Tengok senarai warning user")
@app_commands.describe(user="User yang nak tengok warning")
async def warnings(interaction: discord.Interaction, user: discord.Member):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    key = f"warnings_{interaction.guild.id}_{user.id}"
    warn_list = list(db.get(key) or [])

    embed = discord.Embed(
        title=f"⚠️ Warning History — {user}",
        color=discord.Color.yellow() if warn_list else discord.Color.green()
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    if not warn_list:
        embed.description = "✅ User ni takde warning langsung!"
    else:
        embed.description = f"**Total: {len(warn_list)} warning**\n"
        for i, w in enumerate(warn_list, 1):
            ts = w.get("timestamp", "")[:10]
            embed.add_field(
                name=f"#{i} — {ts}",
                value=f"**Sebab:** {w['reason']}\n**Oleh:** {w['by']}",
                inline=False
            )

    await interaction.response.send_message(embed=embed)


@tree.command(name="clearwarn", description="Buang warning user [Role Tester+]")
@app_commands.describe(user="User yang nak clear warning", nombor="Nombor warning nak buang (kosongkan untuk clear semua)")
async def clearwarn(interaction: discord.Interaction, user: discord.Member, nombor: int = None):
    if not is_approved(interaction.guild.id):
        await interaction.response.send_message(embed=approval_error(), ephemeral=True)
        return

    tester_role = await get_role(interaction.guild, f"role_tester_{interaction.guild.id}")
    if not is_admin(interaction.user):
        if not tester_role or tester_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Anda perlu role **Tester** atau lebih tinggi.", ephemeral=True)
            return

    key = f"warnings_{interaction.guild.id}_{user.id}"
    warn_list = list(db.get(key) or [])

    if not warn_list:
        await interaction.response.send_message(f"✅ **{user}** takde warning pun.", ephemeral=True)
        return

    if nombor is None:
        db[key] = []
        embed = discord.Embed(
            title="🗑️ Warning Cleared",
            description=f"Semua **{len(warn_list)}** warning **{user.mention}** dah dibuang.",
            color=discord.Color.green()
        )
    else:
        if nombor < 1 or nombor > len(warn_list):
            await interaction.response.send_message(f"❌ Nombor warning tak wujud. User ada **{len(warn_list)}** warning.", ephemeral=True)
            return
        removed = warn_list.pop(nombor - 1)
        db[key] = warn_list
        embed = discord.Embed(
            title="🗑️ Warning Dibuang",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Warning #", value=str(nombor), inline=True)
        embed.add_field(name="Sebab yang dibuang", value=removed["reason"], inline=False)
        embed.add_field(name="Baki Warning", value=str(len(warn_list)), inline=False)

    embed.set_thumbnail(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.event
async def setup_hook():
    await bot.load_extension("cogs.request")
    await bot.tree.sync()
    print("✅ Cogs + Slash commands synced!")
# ─── Bot Events ─────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Bot berjalan sebagai {bot.user}")
    print("✅ Slash commands synced!")
    bot.add_view(VerifyButton())
    print("✅ Persistent views registered!")

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
