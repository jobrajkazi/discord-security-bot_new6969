import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import datetime
import re
import asyncio
from keep_alive import keep_alive

# ========================= BOT SETUP =========================
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

# ========================= FILES =========================
WHITELIST_FILE = 'whitelist.json'
CONFIG_FILE = 'config.json'
LOG_FILE = 'moderation_log.json'

def load_json(file, default):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        with open(file, 'w') as f:
            json.dump(default, f)
        return default

whitelist = load_json(WHITELIST_FILE, {"admins": [], "immune": []})
config = load_json(CONFIG_FILE, {
    "spam_threshold": 5,
    "spam_timeframe": 10,
    "punishment_levels": {"spam": "timeout", "profanity": "timeout", "severe": "kick"},
    "timeout_duration": 300,
    "notification_channel": None,
    "min_account_age_days": 7,
    "warning_limit": 3
})
mod_log = load_json(LOG_FILE, [])

# ========================= FULL PROFANITY FILTER =========================
profanity_patterns = [
    # ==================== ENGLISH ====================
    r'\b(ass|asshole|bastard|bitch|bloody|bollocks|bugger|bullshit|cock|cocksucker|cunt|dick|fuck|fucker|fucking|motherfucker|piss|pissed|pissed off|prick|shit|shite|slut|son of a bitch|twat|wanker)\b',
    
    # ==================== SPANISH / LATIN ====================
    r'\b(puta|puto|mierda|pendejo|pendeja|joder|coño|carajo|hijueputa|hijo de puta|maricón|marica|chinga|chingada|culero|güevón|güevona|pajero|pajera|concha|conchatumadre)\b',
    
    # ==================== GERMAN ====================
    r'\b(scheiße|fick|hure|arschloch|fotze|schwanz|miststück|wixer|wichser|schlampe|fotzen|verdammt|kacke)\b',
    
    # ==================== FRENCH ====================
    r'\b(putain|merde|salope|enculé|connard|connasse|bite|bordel|couilles|cul|fils de pute|ta gueule|trou du cul)\b',
    
    # ==================== ITALIAN ====================
    r'\b(vaffanculo|cazzo|troia|stronzo|figlio di puttana|merda|minchia|cornuto|bastardo|puttana|culo|coglione)\b',
    
    # ==================== POLISH ====================
    r'\b(kurwa|jebać|chuj|pierdolić|pizda|pierdol|suka|pierdol się|jebany|kurwi synu|do jaja|pierdolony)\b',
    
    # ==================== RUSSIAN ====================
    r'\b(блядь|хуй|пизда|ебать|ёб твою мать|сука|блять|хер|гандон|мудак|пидор|заебал|нахуй|ебаный|ёбаный|пиздец|хуйня|еблан|охуеть|заебись|пиздаболь|гондон|манда|ебучий|хуеплёт|хуета|ебарь|сраный|долбоёб)\b',
    
    # ==================== HINDI ====================
    r'\b(बहनचोद|मादरचोद|कमीना|चूतिया|रण्डी|कुतिया|लंड|चूत|गांड|भोसड़ीके|हरामखोर|हरामज़ादा|कुत्ते|कुतिया)\b',
    
    # ==================== BENGALI + BANGLISH (Merged & Expanded) ====================
    r'\b(বোকাচোদা|চোদনবাগীশ|খানকি|মাগি|শুয়ার|কুত্তা|গাধা|বাঁদর|মূর্খ|চোদা|চোদন|চুদিরভাই|মাদারচোদ|বাপরেচোদা|বোনচোদ|ভাগিনেচোদ|মামাচোদ|বাপেরব্যাটা|মায়েরপোলা|বাঁড়া|পুসি|ভোদা|ভোঁদা|বাল|ধন|লেওড়া|বারা|পুটকি|হাওয়ারপোলা|মাগিরপোলা|খানকিরপোলা|কুত্তারবাচ্চা|শালা|শালী|গরুচোদা|বেশ্যা|বেশ্যামাগি|হারামজাদা|হারামখোর|চুদির|চোদাচুদি|পুদি|পুদিনা|লোড়া|লোড়া|বালফাল|বালকামানো|চটেরবাল|হেতামারানিরফোয়া|মাংএরপোলা|পুটকিমারি|কালা|পাজিত|মালাউন|নুনু|ধোন|শওয়া|হাওয়ার ছেলে|ভোদার পোলা|চুদি|চোদানো|ফুদি|ফুদনি|ভগ|ভগা|রান্ডি|কুত্তি|শুয়োরের বাচ্চা|বান্দি|হারামি|হারামজাদী|চোদামারা|চুদামারা|পোড়া|পোড়ামুখি|মরণদোষা|গাধা চোদা|বাঁদর চোদা)\b',
    
    # Banglish / Romanized Bengali (Massive Merged List)
    r'\b(bokachoda|bochoda|boka choda|chodna|chod|chudir bhai|chudir vai|madarchod|madarchud|ma chod|bonchod|bainchod|bhaginchod|mamachod|bapre choda|baper beta|mayer pola|magir pola|khanki|khankir pola|kuttar baccha|shala|goru choda|besha magi|beshyamagi|haramzada|haramkhor|choda|chudir|putki mari|putki|bhoda|voda|bal|dhon|leora|bara|bada|pusi|pusy|haowar pola|hawar pola|mang er pola|chat er bal|bal fela|bal kamano|shuar|kutta|gadha|bandor|chutiya|gaandu|randi|kutiya|loda|choot|gand|bhosdi|bhosdike|londi|randa|chodon|chodonbagish|hetamaranir fua|khanki magi|shala put|shali|bessha|bessha magir pola|bhag|bara leora|dhon dhon|bal bal|putki mar|putki marbo|chodbo|chudbo|tor ma re chod|tor bon re chod|tor bap re|magir chele|kuttar chele|shalar put|shalar beta|gorur baccha|pagol choda|murkh choda|randi magi|lund|lund chus|chut mar|chutia|gaand mar|gaandu|bc mc|mc bc|bhenchod|lundia|chootia|shuarer baccha|kuttar chele)\b',
    
    # ==================== OTHER LANGUAGES ====================
    r'\b(可恶|操|肏|妈的|屄|鸡巴|傻逼|狗日的|王八蛋|贱人|婊子|他妈的|狗屎|猪头|二逼)\b', # Chinese
    r'\b(クソ|ちくしょう|やろう|ばかやろう|あほう|たわけ|糞|野郎|畜生|めくら|きちがい)\b', # Japanese
    r'\b(씨발|개새끼|좆발|미친년|엠창|지랄|썅년|좆같|개좆|병신|썅놈|미친놈|쌉년|좆만이|새끼)\b', # Korean
    r'\b(kurva|píča|prdel|kokot|do prdele|jebat|sráč|picoch|zmrd|hovno)\b', # Czech/Slovak
    r'\b(pula|pizda|futu-ți în cur|muie|cacat|prostu|mă-ti-a-puls|curve|fututi)\b', # Romanian
    r'\b(kurva|jebi se|picka|govno|picka materina|jebo ti pas sve|pička|kurvo glava)\b', # Croatian/Serbian
    r'\b(vittu|perkele|saatana|vittuun|paska|helvetti|kusipää|mulkku|tussu|pillu|perse)\b', # Finnish
    r'\b(kurva|fasz|segg|geci|szar|picsa|fing|anyád|bazd meg)\b', # Hungarian
    r'\b(gamo|skase|malaka|poustis|gamoto|vromoskyla|gamimeni|kariolas|tsoula)\b', # Greek
    r'\b(kao|diu|luk|gau|gong|ham ga chaan|hai|sei lo mo|tsat|lan yeung|diu lei)\b', # Cantonese
    r'\b(deo|lon|cak|may|cho|di|me|con|du|ma|may|tang|na|lon|me|may)\b', # Vietnamese
    r'\b(ai khwai|maeng|hee|khway|kee|nok|hee|khway|madarirpola)\b' # Thai
]

spam_tracker = {}
OWNER_ID = 858482656252657674

# ========================= PERMISSIONS =========================
def has_permission(member, guild):
    if not guild: return False
    if guild.owner and member.id == guild.owner.id: return True
    if discord.utils.get(guild.roles, name="Bot King") in member.roles: return True
    return str(member.id) in whitelist.get("admins", [])

# ========================= EVENTS =========================
@bot.event
async def on_ready():
    await tree.sync()
    print(f'{bot.user.name} is online!')

@bot.event
async def on_guild_join(guild):
    if not discord.utils.get(guild.roles, name="Bot King"):
        await guild.create_role(name="Bot King", color=discord.Color.gold(), permissions=discord.Permissions(administrator=True))
   
    if guild.owner and str(guild.owner.id) not in whitelist["admins"]:
        whitelist["admins"].append(str(guild.owner.id))
        with open(WHITELIST_FILE, 'w') as f:
            json.dump(whitelist, f)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    if not message.guild or has_permission(message.author, message.guild):
        return
    
    # Account age check
    if config.get("min_account_age_days"):
        age = (datetime.datetime.now(datetime.timezone.utc) - message.author.created_at).days
        if age < config["min_account_age_days"]:
            await message.delete()
            try:
                await message.author.send(f"❌ Your account is too new to chat here (minimum {config['min_account_age_days']} days).")
            except:
                pass
            return
    
    await check_spam(message)
    await check_content(message)

# ========================= SECURITY SYSTEM =========================
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
        await notify_admins(message.guild, f"🚨 {message.author.mention} punished for **spam** in {message.channel.mention}")

async def check_content(message):
    content = message.content.lower()
    for pattern in profanity_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            await message.delete()
            await punish_user(message.author, message.guild, "profanity", message.channel)
            await notify_user(message.author, "profanity", message.guild)
            await log_action(message.author, "profanity", message.channel)
            await notify_admins(message.guild, f"🚨 {message.author.mention} punished for **profanity** in {message.channel.mention}")
            break

async def punish_user(user, guild, violation_type, channel=None):
    punishment = config["punishment_levels"].get(violation_type, "timeout")
    if punishment == "timeout":
        try:
            await user.timeout(datetime.timedelta(seconds=config["timeout_duration"]))
        except: pass
    elif punishment == "kick":
        try: await user.kick(reason=f"Automated: {violation_type}")
        except: pass
    elif punishment == "ban":
        try: await user.ban(reason=f"Automated: {violation_type}")
        except: pass

async def notify_user(user, violation_type, guild):
    try:
        msg = f"You were timed out in **{guild.name}** for {violation_type}."
        await user.send(msg)
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
        json.dump(mod_log, f, indent=2)

async def notify_admins(guild, text):
    if config.get("notification_channel"):
        ch = bot.get_channel(int(config["notification_channel"]))
        if ch:
            await ch.send(text)

# ========================= COMMANDS =========================
@bot.command()
async def addadmin(ctx, user: discord.User):
    if str(ctx.author.id) not in whitelist["admins"]:
        return await ctx.send("❌ No permission.")
    if str(user.id) not in whitelist["admins"]:
        whitelist["admins"].append(str(user.id))
        with open(WHITELIST_FILE, 'w') as f: json.dump(whitelist, f)
        await ctx.send(f"✅ {user.mention} added as admin.")

@bot.command()
async def setup(ctx):
    if str(ctx.author.id) not in whitelist["admins"]:
        return await ctx.send("❌ No permission.")
    await ctx.send("✅ Security system is active.")

@tree.command(name="san_set", description="Set current channel as log channel")
async def san_set(interaction: discord.Interaction):
    if not has_permission(interaction.user, interaction.guild):
        return await interaction.response.send_message("❌ No permission!", ephemeral=True)
    config["notification_channel"] = str(interaction.channel_id)
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f)
    await interaction.response.send_message(f"✅ Log channel set: {interaction.channel.mention}")

# ====================== RUN ======================
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
