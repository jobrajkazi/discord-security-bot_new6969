import discord
from discord.ext import commands
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

bot = commands.Bot(command_prefix='!', intents=intents)

# Data storage files
WHITELIST_FILE = 'whitelist.json'
CONFIG_FILE = 'config.json'
LOG_FILE = 'moderation_log.json'

# Initialize data structures
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
        "punishment_levels": {
            "spam": "timeout",
            "profanity": "timeout",
            "severe": "kick"
        },
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

# Profanity filter (multi-language)
profanity_patterns = [
   r'\b(ass|asshole|bastard|bitch|bloody|bollocks|bugger|bullshit|cock|cocksucker|cunt|dick|fuck|fucker|fucking|motherfucker|piss|pissed|pissed off|prick|shit|shite|slut|son of a bitch|twat|wanker)\b',
r'\b(puta|puto|mierda|pendejo|pendeja|joder|coño|carajo|hijueputa|hijo de puta|maricón|marica|chinga|chingada|culero|pendejo|pendeja|güevón|güevona|pajero|pajera|concha|conchatumadre)\b',
r'\b(scheiße|fick|hure|arschloch|fotze|schwanz|miststück|wixer|wichser|schlampe|fotzen|verdammt|kacke)\b',
r'\b(putain|merde|salope|enculé|connard|connasse|bite|bordel|couilles|cul|fils de pute|ta gueule|trou du cul)\b',
r'\b(vaffanculo|cazzo|troia|stronzo|figlio di puttana|merda|minchia|cornuto|bastardo|puttana|culo|coglione)\b',
r'\b(kurwa|jebać|chuj|pierdolić|pizda|pierdol|suka|pierdol się|jebany|kurwi synu|do jaja|pierdolony)\b',
r'\b(блядь|хуй|пизда|ебать|ёб твою мать|сука|блять|хер|гандон|мудак|пидор|заебал|нахуй|ебаный|ёбаный)\b',
r'\b(बहनचोद|मादरचोद|कमीना|चूतिया|मादरचोद|रण्डी|कुतिया|लंड|चूत|गांड|भोसड़ीके|मादरचोद|हरामखोर|हरामज़ादा|कुत्ते|कुतिया)\b',
r'\b(বোকাচোদা|চোদনবাগীশ|খানকি|মাগি|শুয়ার|কুত্তা|গাধা|বাঁদর|মূর্খ|চোদা|চোদন|চুদিরভাই|মাদারচোদ|বাপরেচোদা|বোনচোদ|ভাগিনেচোদ|মামাচোদ|বাপেরব্যাটা|মায়েরপোলা|বাঁড়া|পুসি)\b',
r'\b(可恶|操|肏|妈的|屄|鸡巴|傻逼|狗日的|王八蛋|贱人|婊子|他妈的|狗屎|猪头|二逼)\b',
r'\b(クソ|ちくしょう|やろう|ばかやろう|あほう|たわけ|糞|野郎|畜生|めくら|きちがい)\b',
r'\b(씨발|개새끼|좆발|미친년|엠창|지랄|썅년|좆같|개좆|병신|썅놈|미친놈|쌉년|좆만이|새끼)\b',
r'\b(пиздец|хуйня|еблан|охуеть|заебись|пиздаболь|гондон|манда|ебучий|хуеплёт|хуета|ебарь|сраный|долбоёб)\b',
r'\b(kurva|píča|prdel|kokot|do prdele|jebat|sráč|picoch|kurva|zmrd|hovno)\b',
r'\b(pula|pizda|futu-ți în cur|muie|cacat|prostu|mă-ti-a-puls|curve|fututi)\b',
r'\b(kurva|jebi se|picka|govno|picka materina|jebo ti pas sve|pička|kurvo glava)\b',
r'\b(kurwa|pizda|jebać|chuj|pierdolić|suka|pierdol|pizda|jebany|kurwi)\b',
r'\b(puta|merda|caralho|foda-se|filho da puta|cona|porra|desgraça|viado|paneleiro)\b',
r'\b(vittu|perkele|saatana|vittuun|paska|helvetti|kusipää|mulkku|tussu|pillu|perse)\b',
r'\b(kurva|fasz|segg|geci|szar|picsa|fing|anyád|bazd meg)\b',
r'\b(gamo|skase|malaka|poustis|gamoto|vromoskyla|gamimeni|kariolas|tsoula)\b',
r'\b(blyat|khuy|pizda|yobat|suka|yob tvoyu mat|gandon|mudak|pidor|zaebal|nakhuy|ebany)\b',
r'\b(putain|merde|salope|enculé|connard|bite|bordel|couilles|cul|fils de pute|ta gueule)\b',
r'\b(puta|mierda|pendejo|joder|coño|hijueputa|maricón|chinga|culero|pendeja|güevón)\b',
r'\b(scheiße|fick|hure|arschloch|fotze|schwanz|miststück|wixer|wichser|schlampe)\b',
r'\b(vaffanculo|cazzo|troia|stronzo|figlio di puttana|merda|minchia|cornuto|bastardo)\b',
r'\b(kurwa|jebać|chuj|pierdolić|pizda|pierdol|suka|jebany|kurwi synu|do jaja)\b',
r'\b(bokachoda|chodonbagish|khanki|magi|shuar|kutta|gadha|bandor|murkho|choda|chodon|chudir bhai|madarchod|bapre choda|bonchod|bhaginechod|mamachod|baper beta|mayer pola|bada|pussi)\b',
r'\b(bhenchod|madarchod|chutiya|gaandu|randi|kutiya|loda|choot|gand|bhosdike|madarchod|haramkhor|haramzada|kutte|kutiya)\b',
r'\b(kao|diu|luk|gau|gong|ham ga chaan|hai|sei lo mo|tsat|lan yeung|diu lei)\b',
r'\b(kuso|chikusho|yarou|bakayarou|ahou|take|kuso|yarou|chikushou|bakayarou)\b',
r'\b(ssibal|kkaesaekki|jotbal|michinnyeon|jil|nom|nyeon|saekki|shibal|gae|miyeon|nom|sseon|nyeon)\b',
r'\b(deo|lon|cak|may|cho|di|me|con|du|ma|may|tang|na|lon|me|may|lon|me|may)\b',
r'\b(ai khwai|maeng|hee|khway|kee|nok|hee|khway|maeng|hee|khway|madarirpola\b',
]
# Spam detection
spam_tracker = {}

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')
    
    for guild in bot.guilds:
        await setup_control_panel(guild)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if str(message.author.id) in whitelist["admins"] or str(message.author.id) in whitelist["immune"]:
        return
    
    await bot.process_commands(message)
    await check_spam(message)
    await check_content(message)

async def check_spam(message):
    user_id = str(message.author.id)
    current_time = datetime.datetime.now().timestamp()
    
    if user_id not in spam_tracker:
        spam_tracker[user_id] = []
    
    spam_tracker[user_id].append(current_time)
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if current_time - t <= config["spam_timeframe"]]
    
    if len(spam_tracker[user_id]) > config["spam_threshold"]:
        await punish_user(message.author, message.guild, "spam", message.channel)
        await notify_user(message.author, "spam", message.guild)
        await log_action(message.author, "spam", message.channel)
        await notify_admins(message.guild, f"User {message.author.mention} was punished for spam in {message.channel.mention}")

async def check_content(message):
    content = message.content.lower()
    
    for pattern in profanity_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            await punish_user(message.author, message.guild, "profanity", message.channel)
            await notify_user(message.author, "profanity", message.guild)
            await log_action(message.author, "profanity", message.channel)
            await notify_admins(message.guild, f"User {message.author.mention} was punished for profanity in {message.channel.mention}")
            await message.delete()
            break

async def punish_user(user, guild, violation_type, channel):
    punishment = config["punishment_levels"].get(violation_type, "timeout")
    
    if punishment == "timeout":
        try:
            await user.timeout(datetime.timedelta(seconds=config["timeout_duration"]))
        except:
            await channel.send(f"Could not timeout {user.mention}. Missing permissions.")
    elif punishment == "kick":
        try:
            await user.kick(reason=f"Automated punishment for {violation_type}")
        except:
            await channel.send(f"Could not kick {user.mention}. Missing permissions.")
    elif punishment == "ban":
        try:
            await user.ban(reason=f"Automated punishment for {violation_type}")
        except:
            await channel.send(f"Could not ban {user.mention}. Missing permissions.")

async def notify_user(user, violation_type, guild):
    try:
        if violation_type == "spam":
            message = f"You have been timed out for 5 minutes in {guild.name} for spamming messages."
        elif violation_type == "profanity":
            message = f"You have been timed out for 5 minutes in {guild.name} for using profanity."
        
        await user.send(message)
    except:
        pass

async def log_action(user, action, channel):
    log_entry = {
        "user_id": str(user.id),
        "username": str(user),
        "action": action,
        "channel_id": str(channel.id),
        "channel_name": channel.name,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    mod_log.append(log_entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(mod_log, f)

async def notify_admins(guild, message):
    notification_channel_id = config.get("notification_channel")
    
    if notification_channel_id:
        notification_channel = bot.get_channel(int(notification_channel_id))
        if notification_channel:
            await notification_channel.send(message)
            return
    
    for channel in guild.text_channels:
        if "admin" in channel.name.lower() or "mod" in channel.name.lower():
            await channel.send(message)
            return
    
    try:
        await guild.owner.send(message)
    except:
        pass

async def setup_control_panel(guild):
    control_panel_channel = None
    for channel in guild.text_channels:
        if channel.name == "security-bot-control":
            control_panel_channel = channel
            break
    
    if not control_panel_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
        }
        
        for admin_id in whitelist["admins"]:
            member = guild.get_member(int(admin_id))
            if member:
                overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        control_panel_channel = await guild.create_text_channel(
            "security-bot-control",
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title="Security Bot Control Panel",
            description="Use the buttons below to manage the security bot",
            color=discord.Color.blue()
        )
        
        await control_panel_channel.send(embed=embed)

# Admin commands
@bot.command(name='addadmin')
async def add_admin(ctx, user: discord.User):
    if str(ctx.author.id) not in whitelist["admins"]:
        return await ctx.send("You don't have permission to use this command.")
    
    if str(user.id) not in whitelist["admins"]:
        whitelist["admins"].append(str(user.id))
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(whitelist, f)
        await ctx.send(f"{user.mention} has been added to the admin whitelist.")
    else:
        await ctx.send(f"{user.mention} is already an admin.")

@bot.command(name='removeadmin')
async def remove_admin(ctx, user: discord.User):
    if str(ctx.author.id) not in whitelist["admins"]:
        return await ctx.send("You don't have permission to use this command.")
    
    if str(user.id) in whitelist["admins"]:
        whitelist["admins"].remove(str(user.id))
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(whitelist, f)
        await ctx.send(f"{user.mention} has been removed from the admin whitelist.")
    else:
        await ctx.send(f"{user.mention} is not an admin.")

@bot.command(name='unban')
async def unban_user(ctx, user_id: int):
    if str(ctx.author.id) not in whitelist["admins"]:
        return await ctx.send("You don't have permission to use this command.")
    
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason="Unbanned by security bot admin command")
        await ctx.send(f"✅ Successfully unbanned **{user}**.")
        await log_action(user, "unban", ctx.channel)
        await notify_admins(ctx.guild, f"🔓 {ctx.author.mention} unbanned {user}.")
    except discord.NotFound:
        await ctx.send("❌ User not found or not banned.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unban users.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name='setup')
async def setup_bot(ctx):
    if str(ctx.author.id) not in whitelist["admins"]:
        return await ctx.send("No permission.")
    
    await setup_control_panel(ctx.guild)
    await ctx.send("✅ Security bot control panel has been set up!")

# ------------------- BOT TOKEN & RUN -------------------
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN environment variable not found!")
    else:
        bot.run(MTUwMTk5ODIwMjI5ODMwMjU3NA.GjAHTf.utdWZ-1Wtc6nXeRSzfT856xBsxXujj6TPB-I28)
