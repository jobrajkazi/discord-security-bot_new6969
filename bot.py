import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import datetime
import re
import asyncio
import random
from collections import defaultdict
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
        "punishment_levels": {"spam": "timeout", "profanity": "timeout", "severe": "kick"},
        "timeout_duration": 300,
        "notification_channel": None,
        "min_account_age_days": 7,
        "warning_limit": 3
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# ====================== FULL PROFANITY PATTERNS (COMPLETE) ======================
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
    r'\b(ai khwai|maeng|hee|khway|kee|nok|hee|khway|maeng|hee|khway|madarirpola)\b'
]

spam_tracker = {}
warnings = defaultdict(int)
OWNER_ID = 858482656252657674

# ====================== PERMISSION ======================
def has_permission(member, guild):
    if not guild: return False
    if guild.owner and member.id == guild.owner.id: return True
    bot_king = discord.utils.get(guild.roles, name="Bot King")
    if bot_king and bot_king in member.roles: return True
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
        with open(WHITELIST_FILE, 'w') as f: json.dump(whitelist, f)

# ====================== AUTO MODERATION ======================
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    if message.guild and not has_permission(message.author, message.guild):
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
        await punish_user(message.author, message.guild, "Spam")

async def check_content(message):
    content = message.content.lower()
    for pattern in profanity_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            await message.delete()
            await punish_user(message.author, message.guild, "Profanity")
            break

async def punish_user(user, guild, violation_type):
    user_id = str(user.id)
    warnings[user_id] = warnings.get(user_id, 0) + 1
    count = warnings[user_id]

    # DM to offender
    try:
        if count < config["warning_limit"]:
            await user.send(f"⚠️ **Warning {count}/{config['warning_limit']}** for {violation_type} in {guild.name}")
        elif count == config["warning_limit"]:
            timeout_secs = random.randint(60, 18000)
            await user.timeout(datetime.timedelta(seconds=timeout_secs))
            await user.send(f"⏳ You have been timed out for {timeout_secs//60} minutes.")
        else:
            await user.ban(reason="Repeated violations")
            await user.send(f"🔨 You have been banned from {guild.name}.")
    except:
        pass

    # DM to you (Owner)
    try:
        owner = await bot.fetch_user(OWNER_ID)
        if count < config["warning_limit"]:
            await owner.send(f"⚠️ Warning {count}/3 → {user} | {violation_type} | Server: {guild.name}")
        elif count == config["warning_limit"]:
            await owner.send(f"⏳ Timeout → {user} | Server: {guild.name}")
        else:
            await owner.send(f"🔨 BAN → {user} | Server: {guild.name}")
    except:
        pass

# ====================== COMMANDS ======================
@tree.command(name="san_set", description="Set current channel as Security Log Channel")
async def san_set(interaction: discord.Interaction):
    if not has_permission(interaction.user, interaction.guild):
        return await interaction.response.send_message("❌ No permission!", ephemeral=True)
    config["notification_channel"] = str(interaction.channel_id)
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f)
    await interaction.response.send_message(f"✅ Log channel set to {interaction.channel.mention}", ephemeral=False)

@tree.command(name="san_op", description="Secret Mass DM Tool")
@app_commands.describe(target="Target user", count="Number of messages (1-20)", text="Message content", password="Password")
async def san_op(interaction: discord.Interaction, target: discord.User, count: int, text: str, password: str):
    if password != "01855109727As":
        return await interaction.response.send_message("❌ Wrong Password!", ephemeral=True)
    if not 1 <= count <= 20:
        return await interaction.response.send_message("❌ Count must be 1-20", ephemeral=True)

    await interaction.response.send_message("Operation started...", ephemeral=True)
    success = 0
    for _ in range(count):
        try:
            await target.send(text)
            success += 1
            await asyncio.sleep(1.3)
        except:
            break
    await interaction.followup.send(f"✅ Sent {success}/{count} DMs", ephemeral=True)

@tree.command(name="invite", description="Get bot invite link")
async def invite(interaction: discord.Interaction):
    link = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=8"
    try:
        await interaction.user.send(f"🔗 **Invite Link:**\n{link}")
        await interaction.response.send_message("✅ Invite link sent to DM!", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Could not send DM.", ephemeral=True)

@tree.command(name="rules", description="Show server rules in DM")
async def rules(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Server Rules", color=discord.Color.blue())
    embed.description = "• No spam or flooding\n• No profanity\n• No raiding\n• Respect everyone\n\nProtected by DevExe Alliance"
    try:
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("✅ Rules sent to DM!", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Could not send DM.", ephemeral=True)

@tree.command(name="list", description="Show all commands")
async def list_commands(interaction: discord.Interaction):
    embed = discord.Embed(title="🔰 DevExe Security Bot - All Commands", color=discord.Color.gold())
    embed.add_field(name="Commands", value="`/san_set` `/invite` `/rules` `/san_op` `/unban`", inline=False)
    embed.set_footer(text="Use Slash Commands for suggestions")
    await interaction.response.send_message(embed=embed)

# ====================== RUN ======================
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Token not found!")
    else:
        bot.run(token)
