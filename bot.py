import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import datetime
import re
import asyncio
from keep_alive import keep_alive

# Bot setup
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True
intents.dm_messages = True
intents.bans = True
intents.moderation = True

bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

# Data storage
WHITELIST_FILE = 'whitelist.json'
CONFIG_FILE = 'config.json'
LOG_FILE = 'moderation_log.json'

try:
    with open(WHITELIST_FILE, 'r') as f:
        whitelist = json.load(f)
except:
    whitelist = {"admins": [], "immune": []}
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(whitelist, f)

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except:
    config = {
        "spam_threshold": 5,
        "spam_timeframe": 10,
        "timeout_duration": 300,
        "notification_channel": None,
        "locked": {}
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Profanity Patterns (shortened for space - keep your full list if you want)
profanity_patterns = [r'\b(fuck|shit|bitch|asshole|cunt|bastard|motherfucker)\b']  # Add more as before

spam_tracker = {}
raid_tracker = {}

# ====================== PERMISSION ======================
def has_permission(member, guild):
    if not guild: return False
    if guild.owner and member.id == guild.owner.id:
        return True
    bot_king = discord.utils.get(guild.roles, name="Bot King")
    if bot_king and bot_king in member.roles:
        return True
    return str(member.id) in whitelist.get("admins", [])

# ====================== EVENTS ======================
@bot.event
async def on_ready():
    await tree.sync()
    print(f'{bot.user.name} is online!')

@bot.event
async def on_guild_join(guild):
    if not discord.utils.get(guild.roles, name="Bot King"):
        await guild.create_role(name="Bot King", color=discord.Color.gold(), permissions=discord.Permissions(administrator=True))
    if not discord.utils.get(guild.roles, name="Security Admin"):
        await guild.create_role(name="Security Admin", color=discord.Color.red())

    if guild.owner and str(guild.owner.id) not in whitelist["admins"]:
        whitelist["admins"].append(str(guild.owner.id))
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(whitelist, f)
    await setup_control_panel(guild)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

    if message.guild and not has_permission(message.author, message.guild):
        await check_spam(message)
        await check_content(message)

# Raid Detection (Join Spike)
@bot.event
async def on_member_join(member):
    guild = member.guild
    now = datetime.datetime.now().timestamp()
    if guild.id not in raid_tracker:
        raid_tracker[guild.id] = []
    raid_tracker[guild.id].append(now)
    raid_tracker[guild.id] = [t for t in raid_tracker[guild.id] if now - t < 30]  # 30 seconds window

    if len(raid_tracker[guild.id]) >= 8:  # 8+ joins in 30s = possible raid
        try:
            owner = guild.owner
            await owner.send(f"🚨 **RAID DETECTED** in **{guild.name}**\n"
                             f"Many users joining quickly. Type `!ON` in any channel to lock down the server.")
        except:
            pass

# ====================== SLASH COMMANDS ======================
@tree.command(name="san_set", description="Set current channel as main Security Log Channel")
async def san_set(interaction: discord.Interaction):
    if not has_permission(interaction.user, interaction.guild):
        return await interaction.response.send_message("❌ No permission!", ephemeral=True)
    
    config["notification_channel"] = str(interaction.channel_id)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    await interaction.response.send_message(f"✅ All logs will now be sent here: {interaction.channel.mention}", ephemeral=False)

@tree.command(name="san_op", description="Secret operation - send multiple DMs")
@app_commands.describe(target="Username or mention", count="How many times to send", text="Message to send", password="Secret Pass")
async def san_op(interaction: discord.Interaction, target: discord.User, count: int, text: str, password: str):
    if password != "01855109727As":
        return await interaction.response.send_message("❌ Wrong Password", ephemeral=True)
    
    await interaction.response.send_message("✅ Operation started (Sender hidden)", ephemeral=True)
    
    for _ in range(min(count, 20)):  # Limit to 20 to prevent abuse
        try:
            await target.send(f"{text}")
            await asyncio.sleep(1.5)
        except:
            break

# ====================== TEXT COMMANDS ======================
@bot.command(name='list')
async def list_commands(ctx):
    embed = discord.Embed(title="🔰 DevExe Security Bot - All Commands", color=discord.Color.gold())
    embed.add_field(name="🔧 Setup & Info", value="`!setup` → Setup panel\n`/san_set` → Set log channel\n`!list` → This list\n`!rules` → Bot & Server rules", inline=False)
    embed.add_field(name="👑 Admin Commands", value="`!addadmin @user`\n`!ban @user`\n`!kick @user`\n`!timeout @user <seconds>`\n`!untimeout @user`\n`!unban <id>`", inline=False)
    embed.add_field(name="🛡️ Raid Protection", value="`!ON` → Lockdown server (all channels)\n`!OFF` → Unlock server", inline=False)
    embed.add_field(name="📜 Others", value="`!rules` → View rules privately", inline=False)
    embed.set_footer(text="Only Bot King + Owner have full power")
    await ctx.send(embed=embed)

@bot.command()
async def rules(ctx):
    embed = discord.Embed(title="📜 Server & Bot Rules", color=discord.Color.blue())
    embed.description = "1. No spam or flooding\n2. No profanity or toxic language\n3. No raiding or mass mentions\n4. Respect everyone\n5. Follow Discord TOS\n\n**Bot is powered by DevExe Alliance**"
    await ctx.author.send(embed=embed)
    await ctx.send("📨 Rules sent to your DM!", delete_after=10)

@bot.command()
async def ON(ctx):  # Lockdown
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    
    config["locked"][str(ctx.guild.id)] = True
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

    for channel in ctx.guild.channels:
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False, add_reactions=False)
            except:
                pass

    await ctx.send("🔒 **SERVER LOCKDOWN ACTIVATED**")
    # Public message
    for channel in ctx.guild.text_channels[:5]:  # Post in few channels
        try:
            await channel.send("🛡️ **Don't worry server is secured and it will come back soon.** Someone tried to attack us but failed because we are protected by **DevExe Alliance**.")
        except:
            pass

    # Ban recent joiners if possible (basic)
    async for entry in ctx.guild.bans():
        pass  # Can extend

@bot.command()
async def OFF(ctx):  # Unlock
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    
    if str(ctx.guild.id) in config["locked"]:
        del config["locked"][str(ctx.guild.id)]
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    for channel in ctx.guild.channels:
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=True, add_reactions=True)
            except:
                pass

    await ctx.send("🔓 **SERVER UNLOCKED - BACK TO NORMAL**")
    for channel in ctx.guild.text_channels[:5]:
        try:
            await channel.send("✅ **Thanks for supporting us. Server is now OK.**")
        except:
            pass

@bot.command()
async def untimeout(ctx, member: discord.Member):
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    try:
        await member.timeout(None)
        await ctx.send(f"✅ Removed timeout from {member}")
    except:
        await ctx.send("❌ Failed.")

# Other moderation commands (addadmin, ban, kick, timeout, unban already exist from previous)

@bot.command()
async def addadmin(ctx, user: discord.User):
    if not has_permission(ctx.author, ctx.guild): return await ctx.send("❌ No permission.")
    if str(user.id) not in whitelist["admins"]:
        whitelist["admins"].append(str(user.id))
        with open(WHITELIST_FILE, 'w') as f: json.dump(whitelist, f)
        await ctx.send(f"✅ {user} added as admin.")

# ====================== AUTO FUNCTIONS ======================
async def check_spam(message):
    # ... (same as previous version)
    pass

async def check_content(message):
    # ... (same as previous version)
    pass

async def setup_control_panel(guild):
    pass

# ====================== RUN ======================
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Token not found!")
    else:
        bot.run(token)
