import os
import discord
from keep_alive import keep_alive
from discord import app_commands
from discord.ext import commands
import datetime

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 1. ระบบปุ่มกดรับยศ (Persistent View) คงไว้ตามเดิม
class RoleButtonView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="rexlwhite", style=discord.ButtonStyle.green, custom_id="persistent_role_btn")
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("ไม่พบยศนี้ในเซิร์ฟเวอร์", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"ลบยศ {role.name} ออกจากคุณแล้ว!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"คุณได้รับยศ {role.name} เรียบร้อยแล้ว!", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # รัน View ปุ่มกดรับยศให้ทำงานตลอดเวลาแม้บอทจะรีสตาร์ท (ต้องใส่ Role ID เริ่มต้นในระบบ)
        self.add_view(RoleButtonView(role_id=0))

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        # สั่ง Sync คำสั่งสแลชทั้งหมดเข้า Discord ทันที
        synced = await bot.tree.sync()
        print(f"ลงทะเบียน Slash Command สำเร็จ! จำนวน: {len(synced)} คำสั่ง")
    except Exception as e:
        print(f"ลงทะเบียนคำสั่งล้มเหลว: {e}")

# ==========================================
# 2. [เพิ่มเข้ามาใหม่] ระบบจัดการเซิร์ฟเวอร์ (Moderation)
# ==========================================

# 🛑 คำสั่งเตะสมาชิก (Kick)
@bot.tree.command(name="kick", description="เตะสมาชิกออกจากเซิร์ฟเวอร์")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(member="เลือกสมาชิกที่ต้องการเตะ", reason="เหตุผลในการเตะ")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่ได้ระบุเหตุผล"):
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("คุณไม่สามารถเตะผู้ที่มีตำแหน่งสูงกว่าหรือเท่ากับคุณได้", ephemeral=True)
        return

    try:
        await member.kick(reason=reason)
        embed = discord.Embed(title="สมาชิกถูกเตะ", color=discord.Color.orange())
        embed.add_field(name="ผู้ถูกเตะ", value=member.mention, inline=True)
        embed.add_field(name="ผู้สั่งการ", value=interaction.user.mention, inline=True)
        embed.add_field(name="เหตุผล", value=reason, inline=False)
        embed.set_timestamp()
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"ไม่สามารถเตะสมาชิกได้เนื่องจาก: {e}", ephemeral=True)

# 🚫 คำสั่งแบนสมาชิก (Ban)
@bot.tree.command(name="ban", description="แบนสมาชิกออกจากเซิร์ฟเวอร์")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(member="เลือกสมาชิกที่ต้องการแบน", reason="เหตุผลในการแบน")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่ได้ระบุเหตุผล"):
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("คุณไม่สามารถแบนผู้ที่มีตำแหน่งสูงกว่าหรือเท่ากับคุณได้", ephemeral=True)
        return

    try:
        await member.ban(reason=reason)
        embed = discord.Embed(title="สมาชิกถูกแบน", color=discord.Color.red())
        embed.add_field(name="ผู้ถูกแบน", value=member.mention, inline=True)
        embed.add_field(name="ผู้สั่งการ", value=interaction.user.mention, inline=True)
        embed.add_field(name="เหตุผล", value=reason, inline=False)
        embed.set_timestamp()
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"ไม่สามารถแบนสมาชิกได้เนื่องจาก: {e}", ephemeral=True)

# ⏳ คำสั่งไทม์เอาต์ / ปิดการโต้ตอบ (Timeout / Mute)
@bot.tree.command(name="timeout", description="จำกัดเวลาโต้ตอบสมาชิก (Timeout)")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.choices(duration=[
    app_commands.Choice(name="60 วินาที", value=60),
    app_commands.Choice(name="5 นาที", value=300),
    app_commands.Choice(name="10 นาที", value=600),
    app_commands.Choice(name="1 ชั่วโมง", value=3600),
    app_commands.Choice(name="1 วัน", value=86400),
    app_commands.Choice(name="1 สัปดาห์", value=604800),
])
@app_commands.describe(member="เลือกสมาชิก", duration="ระยะเวลาในการลงโทษ", reason="เหตุผล")
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: app_commands.Choice[int], reason: str = "ไม่ได้ระบุเหตุผล"):
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("คุณไม่สามารถลงโทษผู้ที่มีตำแหน่งสูงกว่าหรือเท่ากับคุณได้", ephemeral=True)
        return

    try:
        td = datetime.timedelta(seconds=duration.value)
        await member.timeout(td, reason=reason)

        embed = discord.Embed(title="สมาชิกถูกจำกัดเวลา", color=discord.Color.gold())
        embed.add_field(name="ผู้ถูกลงโทษ", value=member.mention, inline=True)
        embed.add_field(name="ระยะเวลา", value=duration.name, inline=True)
        embed.add_field(name="ผู้สั่งการ", value=interaction.user.mention, inline=True)
        embed.add_field(name="เหตุผล", value=reason, inline=False)
        embed.set_timestamp()
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"ไม่สามารถตั้งค่าไทม์เอาต์ได้เนื่องจาก: {e}", ephemeral=True)

# 🔓 คำสั่งยกเลิกไทม์เอาต์ (Remove Timeout)
@bot.tree.command(name="untimeout", description="ยกเลิกการจำกัดเวลาโต้ตอบสมาชิก")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(member="เลือกสมาชิกที่ต้องการปลดล็อก")
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None)
        await interaction.response.send_message(f"ปลดล็อกการจำกัดเวลาของ {member.mention} เรียบร้อยแล้ว")
    except Exception as e:
        await interaction.response.send_message(f"ไม่สามารถยกเลิกไทม์เอาต์ได้เนื่องจาก: {e}", ephemeral=True)

# 🧹 คำสั่งล้างข้อความ (Clear / Purge)
@bot.tree.command(name="clear", description="ลบข้อความในห้องแชทจำนวนมาก")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="จำนวนข้อความที่ต้องการลบ (สูงสุด 100)")
async def clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("กรุณาระบุจำนวนข้อความระหว่าง 1 ถึง 100", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True) # ป้องกันบอทค้างหากลบเยอะ
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"ลบข้อความเรียบร้อยแล้วทั้งหมด {len(deleted)} ข้อความ", ephemeral=True)

# ==========================================
# 3. [ระบบเดิม] คำสั่งสร้างกล่องรับยศ Embed 
# ==========================================
@bot.tree.command(name="verify", description="สร้างกล่องรับยศส่งไปยังห้องที่กำหนด")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.choices(color=[
    app_commands.Choice(name="แดง", value="red"),
    app_commands.Choice(name="น้ำเงิน", value="blue"),
    app_commands.Choice(name="เขียว", value="green"),
    app_commands.Choice(name="เหลือง", value="gold"),
    app_commands.Choice(name="ม่วง", value="purple"),
])
async def verify(
    interaction: discord.Interaction, 
    channel_id: str, 
    role: discord.Role, 
    title: str, 
    description: str, 
    mention_role: discord.Role = None, 
    color: str = "blue",
    image_url: str = None,
    thumbnail_url: str = None
):
    try:
        target_channel = bot.get_channel(int(channel_id))
        if target_channel is None:
            target_channel = await bot.fetch_channel(int(channel_id))
    except Exception:
        await interaction.response.send_message("ไม่พบห้องแชทนี้ กรุณาตรวจสอบ Channel ID ให้ถูกต้อง", ephemeral=True)
        return

    color_map = {"red": discord.Color.red(), "blue": discord.Color.blue(), "green": discord.Color.green(), "gold": discord.Color.gold(), "purple": discord.Color.purple()}
    embed_color = color_map.get(color, discord.Color.blue())

    embed = discord.Embed(title=title, description=description, color=embed_color)
    embed.add_field(name="ยศที่จะได้รับเมื่อกดปุ่ม", value=role.mention, inline=False)
    embed.set_footer(text=f"สร้างโดย {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    if image_url and image_url.startswith(("http://", "https://")):
        embed.set_image(url=image_url)
    if thumbnail_url and thumbnail_url.startswith(("http://", "https://")):
        embed.set_thumbnail(url=thumbnail_url)

    content_message = f"แจ้งเตือนกลุ่มยศ: {mention_role.mention}" if mention_role else ""

    view = RoleButtonView(role_id=role.id)
    await target_channel.send(content=content_message, embed=embed, view=view)
    await interaction.response.send_message(f"ส่งกล่องรับยศไปยังห้อง {target_channel.mention} เรียบร้อยแล้ว!", ephemeral=True)

keep_alive()

bot.run(os.getenv('TOKEN'))