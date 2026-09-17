import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import datetime
import random
import os

# تحميل المتغيرات البيئية
load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="", intents=intents)

ADMIN_ROLE_NAME = "Admin"  # اسم رتبة الأدمن المصرح لها

# ==========================================
# دالة التحقق من الصلاحيات وحماية هرمية الرتب
# ==========================================
def can_moderate_member(issuer: discord.Member, target: discord.Member) -> bool:
    if issuer.id == issuer.guild.owner_id:
        return True
    return issuer.top_role > target.top_role

def is_admin_interaction():
    async def predicate(interaction: discord.Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=ADMIN_ROLE_NAME)
        if role is None and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ ليس لديك الصلاحية لاستخدام هذا الأمر!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

def is_admin_ctx():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=ADMIN_ROLE_NAME)
        if role is None and not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر!")
            return False
        return True
    return commands.check(predicate)

# قواعد البيانات المؤقتة
warnings = {}      
user_balances = {}  
user_inventory = {} 
market_prices = {"الماس": 100, "ذهب": 50, "نحاس": 20, "حديد": 10, "يورانيوم": 200, "وقود": 30}

@bot.event
async def on_ready():
    print(f'تم تشغيل البوت بنجاح باسم: {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"تم مزامنة {len(synced)} أمر سلاش بنجاح!")
    except Exception as e:
        print(f"خطأ في المزامنة: {e}")
    update_prices.start()

@tasks.loop(minutes=10)
async def update_prices():
    for item in market_prices:
        change = random.randint(-10, 10)
        market_prices[item] = max(1, market_prices[item] + change)

# ==========================================
# 1. أوامر السلاش (باللغة الإنجليزية)
# ==========================================

@bot.tree.command(name="ban", description="Ban a member from the server")
@is_admin_interaction()
async def ban_slash(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason provided"):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك تطبيق هذا الأمر على عضو يمتلك رتبة أعلى منك أو تسااويك!", ephemeral=True)
        return
    await member.ban(reason=reason)
    embed = discord.Embed(title="⛔ Ban Executed", color=discord.Color.red())
    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="Duration", value=duration)
    embed.add_field(name="Reason", value=reason)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unban", description="Unban a user by ID")
@is_admin_interaction()
async def unban_slash(interaction: discord.Interaction, user_id: str):
    banned_users = [entry async for entry in interaction.guild.bans()]
    for ban_entry in banned_users:
        if str(ban_entry.user.id) == user_id:
            await interaction.guild.unban(ban_entry.user)
            await interaction.response.send_message(f"✅ Unbanned {ban_entry.user.mention}")
            return
    await interaction.response.send_message("❌ User not found in ban list.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member from the server")
@is_admin_interaction()
async def kick_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك طرد عضو يمتلك رتبة أعلى منك أو تسااويك!", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.tree.command(name="timeout", description="Timeout a member in minutes")
@is_admin_interaction()
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك إعطاء تايم أوت لعضو يمتلك رتبة أعلى منك أو تسااويك!", ephemeral=True)
        return
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"🔇 Timed out {member.mention} for {minutes} minutes.")

@bot.tree.command(name="untimeout", description="Remove timeout from a member")
@is_admin_interaction()
async def untimeout_slash(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 Removed timeout from {member.mention}")

@bot.tree.command(name="serverinfo", description="Display server information")
async def serverinfo_slash(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.blue())
    embed.add_field(name="ID", value=guild.id)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Owner", value=guild.owner.mention)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addrole", description="Add a role to a member")
@is_admin_interaction()
async def addrole_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك التعديل على رتب عضو أعلى منك!", ephemeral=True)
        return
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ Added {role.name} to {member.mention}")

@bot.tree.command(name="removerole", description="Remove a role from a member")
@is_admin_interaction()
async def removerole_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك التعديل على رتب عضو أعلى منك!", ephemeral=True)
        return
    await member.remove_roles(role)
    await interaction.response.send_message(f"🗑️ Removed {role.name} from {member.mention}")

@bot.tree.command(name="temprole", description="Give a temporary role in seconds")
@is_admin_interaction()
async def temprole_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role, seconds: int):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك التعديل على رتب عضو أعلى منك!", ephemeral=True)
        return
    await member.add_roles(role)
    await interaction.response.send_message(f"⏱️ Granted {role.name} to {member.mention} for {seconds}s.")
    await asyncio.sleep(seconds)
    await member.remove_roles(role)

@bot.tree.command(name="openchannel", description="Unlock a channel")
@is_admin_interaction()
async def openchannel_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    ch = channel or interaction.channel
    await ch.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f"🔓 Channel unlocked: {ch.mention}")

@bot.tree.command(name="closechannel", description="Lock a channel")
@is_admin_interaction()
async def closechannel_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    ch = channel or interaction.channel
    await ch.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"🔒 Channel locked: {ch.mention}")

@bot.tree.command(name="nick", description="Change member nickname")
@is_admin_interaction()
async def nick_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك تغيير اسم عضو أعلى منك!", ephemeral=True)
        return
    await member.edit(nick=nickname)
    await interaction.response.send_message(f"📝 Nickname changed for {member.mention}")

@bot.tree.command(name="warn", description="Warn a member")
@is_admin_interaction()
async def warn_slash(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not can_moderate_member(interaction.user, member):
        await interaction.response.send_message("❌ لا يمكنك تحذير عضو أعلى منك!", ephemeral=True)
        return
    g_id, u_id = interaction.guild.id, member.id
    warnings.setdefault(g_id, {}).setdefault(u_id, []).append(reason)
    embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.gold())
    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Total Warnings", value=len(warnings[g_id][u_id]))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unwarn", description="Remove last warning from a member")
@is_admin_interaction()
async def unwarn_slash(interaction: discord.Interaction, member: discord.Member):
    g_id, u_id = interaction.guild.id, member.id
    if g_id in warnings and u_id in warnings[g_id] and warnings[g_id][u_id]:
        warnings[g_id][u_id].pop()
        await interaction.response.send_message(f"✅ Removed last warning from {member.mention}")
    else:
        await interaction.response.send_message("❌ No warnings found.", ephemeral=True)

@bot.tree.command(name="warnings", description="Show warnings list")
async def warnings_slash(interaction: discord.Interaction, member: discord.Member = None):
    g_id = interaction.guild.id
    embed = discord.Embed(title="📋 Warnings List", color=discord.Color.orange())
    if member:
        u_warns = warnings.get(g_id, {}).get(member.id, [])
        embed.description = "\n".join([f"{i+1}. {w}" for i, w in enumerate(u_warns)]) if u_warns else "No warnings."
    else:
        all_w = warnings.get(g_id, {})
        embed.description = "".join([f"<@{uid}>: {len(w)} warnings\n" for uid, w in all_w.items() if w]) or "No warnings."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="giveaway", description="Start a giveaway")
@is_admin_interaction()
async def giveaway_slash(interaction: discord.Interaction, seconds: int, prize: str):
    embed = discord.Embed(title="🎉 Giveaway!", description=f"Prize: **{prize}**\nReact with 🎉 to join!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")
    await asyncio.sleep(seconds)
    n_msg = await interaction.channel.fetch_message(msg.id)
    users = [u for u in [user async for user in n_msg.reactions[0].users()] if not u.bot]
    if users:
        await interaction.channel.send(f"🎊 Winner of **{prize}**: {random.choice(users).mention}!")
    else:
        await interaction.channel.send("❌ No participants.")

@bot.tree.command(name="market", description="Show market prices")
async def market_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📈 Market Prices", color=discord.Color.blue())
    for item, price in market_prices.items():
        embed.add_field(name=item, value=f"{price} cash", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy", description="Buy items from market")
async def buy_slash(interaction: discord.Interaction, item: str, amount: int):
    if item not in market_prices:
        await interaction.response.send_message("❌ Item invalid.", ephemeral=True)
        return
    cost = market_prices[item] * amount
    g_id, u_id = interaction.guild.id, interaction.user.id
    bal = user_balances.setdefault(g_id, {}).setdefault(u_id, 1000)
    if bal < cost:
        await interaction.response.send_message("❌ Not enough cash.", ephemeral=True)
        return
    user_balances[g_id][u_id] -= cost
    inv = user_inventory.setdefault(g_id, {}).setdefault(u_id, {})
    inv[item] = inv.get(item, 0) + amount
    await interaction.response.send_message(f"✅ Purchased {amount} {item}!")

@bot.tree.command(name="sell", description="Sell items to market")
async def sell_slash(interaction: discord.Interaction, item: str, amount: int):
    g_id, u_id = interaction.guild.id, interaction.user.id
    inv = user_inventory.get(g_id, {}).get(u_id, {})
    if inv.get(item, 0) < amount:
        await interaction.response.send_message("❌ Not enough items.", ephemeral=True)
        return
    rev = market_prices[item] * amount
    inv[item] -= amount
    user_balances[g_id][u_id] = user_balances.get(g_id, {}).get(u_id, 1000) + rev
    await interaction.response.send_message(f"💰 Sold {amount} {item} for {rev} cash!")

@bot.tree.command(name="trade", description="Trade cash")
async def trade_slash(interaction: discord.Interaction, amount: int):
    g_id, u_id = interaction.guild.id, interaction.user.id
    bal = user_balances.setdefault(g_id, {}).setdefault(u_id, 1000)
    if bal < amount:
        await interaction.response.send_message("❌ Insufficient funds.", ephemeral=True)
        return
    if random.choice(["win", "lose"]) == "win":
        profit = int(amount * random.uniform(0.1, 0.8))
        user_balances[g_id][u_id] += profit
        await interaction.response.send_message(f"📈 Won {profit} cash!")
    else:
        loss = int(amount * random.uniform(0.1, 0.5))
        user_balances[g_id][u_id] -= loss
        await interaction.response.send_message(f"📉 Lost {loss} cash.")

@bot.tree.command(name="leaderboard", description="Top 10 richest members")
async def leaderboard_slash(interaction: discord.Interaction):
    g_id = interaction.guild.id
    top = sorted(user_balances.get(g_id, {}).items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Top 10 Leaderboard", color=discord.Color.gold())
    embed.description = "\n".join([f"**#{i+1}** <@{uid}> — {b} cash" for i, (uid, b) in enumerate(top)]) if top else "No data."
    await interaction.response.send_message(embed=embed)

# ==========================================
# 2. الأوامر الكتابية (باللغة العربية)
# ==========================================

@bot.command(name="حظر")
@is_admin_ctx()
async def ban_txt(ctx, member: discord.Member, duration: str, *, reason="لا يوجد سبب"):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك تطبيق هذا الأمر على عضو يمتلك رتبة أعلى منك أو تسااويك!")
        return
    await member.ban(reason=reason)
    await ctx.send(f"⛔ تم حظر {member.mention} لمدة {duration} | السبب: {reason}")

@bot.command(name="فك_حظر")
@is_admin_ctx()
async def unban_txt(ctx, *, user_id: str):
    banned_users = [entry async for entry in ctx.guild.bans()]
    for ban_entry in banned_users:
        if str(ban_entry.user.id) == user_id:
            await ctx.guild.unban(ban_entry.user)
            await ctx.send(f"✅ تم فك الحظر عن {ban_entry.user.mention}")
            return
    await ctx.send("❌ لم يتم العثور على العضو.")

@bot.command(name="طرد")
@is_admin_ctx()
async def kick_txt(ctx, member: discord.Member, *, reason="لا يوجد سبب"):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك طرد عضو يمتلك رتبة أعلى منك أو تسااويك!")
        return
    await member.kick(reason=reason)
    await ctx.send(f"👢 تم طرد {member.mention} | السبب: {reason}")

@bot.command(name="تايم")
@is_admin_ctx()
async def timeout_txt(ctx, member: discord.Member, minutes: int, *, reason="لا يوجد سبب"):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك إعطاء تايم أوت لعضو يمتلك رتبة أعلى منك أو تسااويك!")
        return
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"🔇 تم تطبيق تايم أوت على {member.mention} لمدة {minutes} دقيقة.")

@bot.command(name="تكلم")
@is_admin_ctx()
async def untimeout_txt(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 تم إزالة التايم أوت عن {member.mention}")

@bot.command(name="سيرفر")
async def serverinfo_txt(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"معلومات سيرفر {guild.name}", color=discord.Color.blue())
    embed.add_field(name="معرف السيرفر", value=guild.id)
    embed.add_field(name="الأعضاء", value=guild.member_count)
    embed.add_field(name="المالك", value=guild.owner.mention)
    await ctx.send(embed=embed)

@bot.command(name="رول")
@is_admin_ctx()
async def addrole_txt(ctx, member: discord.Member, role: discord.Role):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك التعديل على رتب عضو أعلى منك!")
        return
    await member.add_roles(role)
    await ctx.send(f"✅ تم إعطاء رتبة {role.name} لـ {member.mention}")

@bot.command(name="حذف رول")
@is_admin_ctx()
async def removerole_txt(ctx, member: discord.Member, role: discord.Role):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك التعديل على رتب عضو أعلى منك!")
        return
    await member.remove_roles(role)
    await ctx.send(f"🗑️ تم إزالة رتبة {role.name} من {member.mention}")

@bot.command(name="رول مؤقت")
@is_admin_ctx()
async def temprole_txt(ctx, member: discord.Member, role: discord.Role, seconds: int):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك التعديل على رتب عضو أعلى منك!")
        return
    await member.add_roles(role)
    await ctx.send(f"⏱️ تم إعطاء رتبة {role.name} لـ {member.mention} لمدة {seconds} ثانية.")
    await asyncio.sleep(seconds)
    await member.remove_roles(role)

@bot.command(name="فتح" , name="ف")
@is_admin_ctx()
async def openchannel_txt(ctx, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 تم فتح الروم: {ch.mention}")

@bot.command(name="قفل" , name="ق")
@is_admin_ctx()
async def closechannel_txt(ctx, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 تم قفل الروم: {ch.mention}")

@bot.command(name="لقب")
@is_admin_ctx()
async def nick_txt(ctx, member: discord.Member, *, nickname: str):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك تغيير اسم عضو أعلى منك!")
        return
    await member.edit(nick=nickname)
    await ctx.send(f"📝 تم تغيير اسم {member.mention} إلى: {nickname}")

@bot.command(name="تحذير")
@is_admin_ctx()
async def warn_txt(ctx, member: discord.Member, *, reason: str):
    if not can_moderate_member(ctx.author, member):
        await ctx.send("❌ لا يمكنك تحذير عضو أعلى منك!")
        return
    g_id, u_id = ctx.guild.id, member.id
    warnings.setdefault(g_id, {}).setdefault(u_id, []).append(reason)
    await ctx.send(f"⚠️ تم تحذير {member.mention} | السبب: {reason}")

@bot.command(name="عفو" , name="اعفاء")
@is_admin_ctx()
async def unwarn_txt(ctx, member: discord.Member):
    g_id, u_id = ctx.guild.id, member.id
    if g_id in warnings and u_id in warnings[g_id] and warnings[g_id][u_id]:
        warnings[g_id][u_id].pop()
        await ctx.send(f"✅ تم إزالة آخر تحذير عن {member.mention}")
    else:
        await ctx.send("❌ لا يوجد تحذيرات مسجلة.")

@bot.command(name="التحذيرات")
async def warnings_txt(ctx, member: discord.Member = None):
    g_id = ctx.guild.id
    embed = discord.Embed(title="📋 قائمة التحذيرات", color=discord.Color.orange())
    if member:
        u_warns = warnings.get(g_id, {}).get(member.id, [])
        embed.description = "\n".join([f"{i+1}. {w}" for i, w in enumerate(u_warns)]) if u_warns else "لا يوجد تحذيرات."
    else:
        all_w = warnings.get(g_id, {})
        embed.description = "".join([f"<@{uid}>: {len(w)} تحذيرات\n" for uid, w in all_w.items() if w]) or "لا يوجد تحذيرات."
    await ctx.send(embed=embed)

@bot.command(name="سوق")
async def market_txt(ctx):
    embed = discord.Embed(title="📈 أسعار السوق الحالية", color=discord.Color.blue())
    for item, price in market_prices.items():
        embed.add_field(name=item, value=f"{price} عملة", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="شراء")
async def buy_txt(ctx, item: str, amount: int):
    if item not in market_prices:
        await ctx.send("❌ هذا العنصر غير موجود بالسوق!")
        return
    cost = market_prices[item] * amount
    g_id, u_id = ctx.guild.id, ctx.author.id
    bal = user_balances.setdefault(g_id, {}).setdefault(u_id, 1000)
    if bal < cost:
        await ctx.send("❌ رصيدك غير كافٍ!")
        return
    user_balances[g_id][u_id] -= cost
    inv = user_inventory.setdefault(g_id, {}).setdefault(u_id, {})
    inv[item] = inv.get(item, 0) + amount
    await ctx.send(f"✅ تم شراء {amount} من {item}!")

@bot.command(name="بيع")
async def sell_txt(ctx, item: str, amount: int):
    g_id, u_id = ctx.guild.id, ctx.author.id
    inv = user_inventory.get(g_id, {}).get(u_id, {})
    if inv.get(item, 0) < amount:
        await ctx.send("❌ لا تملك هذه الكمية!")
        return
    rev = market_prices[item] * amount
    inv[item] -= amount
    user_balances[g_id][u_id] = user_balances.get(g_id, {}).get(u_id, 1000) + rev
    await ctx.send(f"💰 تم بيع {amount} من {item} مقابل {rev} عملة!")

@bot.command(name="تداول")
async def trade_txt(ctx, amount: int):
    g_id, u_id = ctx.guild.id, ctx.author.id
    bal = user_balances.setdefault(g_id, {}).setdefault(u_id, 1000)
    if bal < amount:
        await ctx.send("❌ رصيدك غير كافٍ!")
        return
    if random.choice(["win", "lose"]) == "win":
        profit = int(amount * random.uniform(0.1, 0.8))
        user_balances[g_id][u_id] += profit
        await ctx.send(f"📈 تداول ناجح! كسبت {profit} عملة.")
    else:
        loss = int(amount * random.uniform(0.1, 0.5))
        user_balances[g_id][u_id] -= loss
        await ctx.send(f"📉 خسرت بالصفقة {loss} عملة.")

@bot.command(name="الصدارة")
async def leaderboard_txt(ctx):
    g_id = ctx.guild.id
    top = sorted(user_balances.get(g_id, {}).items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 قائمة أفضل 10 متفاعلين", color=discord.Color.gold())
    embed.description = "\n".join([f"**#{i+1}** <@{uid}> — {b} عملة" for i, (uid, b) in enumerate(top)]) if top else "لا توجد بيانات."
    await ctx.send(embed=embed)

# ==========================================
# تشغيل البوت آمن لقراءة التوكين من Render
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("⚠️ لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة!")