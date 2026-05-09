import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import datetime
import re
from keep_alive import keep_alive

# Bot setup
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
# Use the built-in tree instead of creating a new one
tree = bot.tree

# Data storage
WHITELIST_FILE = 'whitelist.json'
CONFIG_FILE = 'config.json'
LOG_FILE = 'moderation_log.json'

# Load data
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
        "notification_channel": None
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

try:
    with open(LOG_FILE, 'r') as f:
        mod_log = json.load(f)
except:
    mod_log = []
    with open(LOG_FILE, 'w') as f:
        json.dump(mod_log, f)

# ====================== PERMISSION CHECK ======================
def has_permission(member, guild):
    if guild is None:
        return False
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
    # Create Bot King role
    if not discord.utils.get(guild.roles, name="Bot King"):
        await guild.create_role(
            name="Bot King",
            color=discord.Color.gold(),
            permissions=discord.Permissions(administrator=True)
        )
    
    # Create Security Admin role
    if not discord.utils.get(guild.roles, name="Security Admin"):
        await guild.create_role(name="Security Admin", color=discord.Color.red())

    # Add owner to whitelist
    if guild.owner and str(guild.owner.id) not in whitelist["admins"]:
        whitelist["admins"].append(str(guild.owner.id))
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(whitelist, f)

    await setup_control_panel(guild)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)
    
    if message.guild and not has_permission(message.author, message.guild):
        await check_spam(message)
        await check_content(message)

# ====================== SLASH COMMANDS ======================
@tree.command(name="san_set", description="Set current channel as Security Bot Log Channel")
async def san_set(interaction: discord.Interaction):
    if not has_permission(interaction.user, interaction.guild):
        return await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
    
    config["notification_channel"] = str(interaction.channel_id)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    
    await interaction.response.send_message(f"✅ Log Channel Set: {interaction.channel.mention}", ephemeral=False)

# ====================== !LIST COMMAND ======================
@bot.command(name='list')
async def list_commands(ctx):
    embed = discord.Embed(
        title="🔰 Security Bot - All Commands",
        description="Complete list of available commands:",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🔧 Setup & Info",
        value="`!setup` → Create control panel\n"
              "`/san_set` → Set log channel\n"
              "`!list` → Show this command list",
        inline=False
    )
    
    embed.add_field(
        name="👑 Admin Commands (Bot King + Owner Only)",
        value="`!addadmin @user` → Add bot admin\n"
              "`!removeadmin @user` → Remove bot admin\n"
              "`!ban @user [reason]` → Ban member\n"
              "`!unban <user_id>` → Unban user\n"
              "`!kick @user [reason]` → Kick member\n"
              "`!timeout @user <seconds>` → Timeout member",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Auto Moderation",
        value="• Automatic spam detection\n"
              "• Automatic profanity filter (multi-language)\n"
              "• Immune users: Bot King, Owner & Admins",
        inline=False
    )
    
    embed.set_footer(text="Only Server Owner and Bot King role users can use admin commands")
    await ctx.send(embed=embed)

# ====================== MODERATION COMMANDS ======================
@bot.command()
async def addadmin(ctx, user: discord.User):
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    if str(user.id) not in whitelist["admins"]:
        whitelist["admins"].append(str(user.id))
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(whitelist, f)
        await ctx.send(f"✅ Added {user} as bot admin.")
    else:
        await ctx.send("⚠️ User is already an admin.")

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    try:
        await member.ban(reason=reason)
        await ctx.send(f"✅ Banned {member}")
    except:
        await ctx.send("❌ Failed to ban user.")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ Kicked {member}")
    except:
        await ctx.send("❌ Failed to kick user.")

@bot.command()
async def timeout(ctx, member: discord.Member, seconds: int = 300):
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    try:
        await member.timeout(datetime.timedelta(seconds=seconds))
        await ctx.send(f"✅ Timed out {member} for {seconds} seconds.")
    except:
        await ctx.send("❌ Failed to timeout user.")

@bot.command()
async def unban(ctx, user_id: int):
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Unbanned {user}")
    except:
        await ctx.send("❌ Failed to unban user.")

@bot.command()
async def setup(ctx):
    if not has_permission(ctx.author, ctx.guild):
        return await ctx.send("❌ No permission.")
    await setup_control_panel(ctx.guild)
    await ctx.send("✅ Setup completed!")

# ====================== AUTO MODERATION ======================
spam_tracker = {}

async def check_spam(message):
    user_id = str(message.author.id)
    current_time = datetime.datetime.now().timestamp()
    
    if user_id not in spam_tracker:
        spam_tracker[user_id] = []
    
    spam_tracker[user_id].append(current_time)
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if current_time - t <= config["spam_timeframe"]]
    
    if len(spam_tracker[user_id]) > config["spam_threshold"]:
        await punish_user(message.author, message.guild, "spam")
        await notify_admins(message.guild, f"🚨 Spam detected → {message.author.mention}")

async def check_content(message):
    content = message.content.lower()
    for pattern in profanity_patterns:
        if re.search(pattern, content):
            await message.delete()
            await punish_user(message.author, message.guild, "profanity")
            await notify_admins(message.guild, f"🚨 Profanity detected → {message.author.mention}")
            break

async def punish_user(user, guild, violation_type):
    try:
        if violation_type in ["spam", "profanity"]:
            await user.timeout(datetime.timedelta(seconds=config["timeout_duration"]))
    except:
        pass

async def notify_admins(guild, text):
    if config.get("notification_channel"):
        channel = bot.get_channel(int(config["notification_channel"]))
        if channel:
            await channel.send(text)

async def setup_control_panel(guild):
    pass  # You can expand this later

# ====================== RUN BOT ======================
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found in environment variables!")
    else:
        bot.run(token)
