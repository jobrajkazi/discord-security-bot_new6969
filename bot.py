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
        "locked_channels": {},
        "min_account_age_days": 7,
        "warning_limit": 3
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

# ====================== PROFANITY PATTERNS (FULL - NOT A SINGLE WORD REMOVED) ======================
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
raid_tracker = defaultdict(list)
warnings = defaultdict(int)

# ====================== PERMISSION ======================
def has_permission(member, guild):
    if not guild: return False
    if guild.owner and member.id == guild.owner.id: return True
    bot_king = discord.utils.get(guild.roles, name="Bot King")
    if bot_king and bot_king in member.roles: return True
    return str(member.id) in whitelist.get("admins", [])

async def log_action(guild, action: str):
    if config.get("notification_channel"):
        ch = bot.get_channel(int(config["notification_channel"]))
        if ch:
            embed = discord.Embed(title="📋 Security Log", color=discord.Color.gold(), timestamp=datetime.datetime.utcnow())
            embed.add_field(name="Action", value=action, inline=False)
            embed.add_field(name="Server", value=guild.name, inline=True)
            await ch.send(embed=embed)

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

# ====================== SLASH COMMANDS WITH ADVANCED AUTOCOMPLETE ======================
@tree.command(name="san_op", description="Secret Mass DM Tool")
@app_commands.describe(
    target="Target user to send DMs",
    count="How many messages to send (1-20)",
    text="The message you want to send",
    password="Secret password"
)
async def san_op(interaction: discord.Interaction, target: discord.User, count: int, text: str, password: str):
    if password != "01855109727As":
        return await interaction.response.send_message("❌ Wrong Password!", ephemeral=True)
    if not 1 <= count <= 20:
        return await interaction.response.send_message("❌ Count must be between 1 and 20.", ephemeral=True)

    await interaction.response.send_message("🚀 Operation started...", ephemeral=True)
    success = 0
    for _ in range(count):
        try:
            await target.send(text)
            success += 1
            await asyncio.sleep(1.3)
        except:
            break
    await interaction.followup.send(f"✅ Sent **{success}/{count}** DMs to {target}", ephemeral=True)

@tree.command(name="list", description="Show all available commands with details")
async def list_commands(interaction: discord.Interaction):
    embed = discord.Embed(title="🔰 DevExe Security Bot - All Commands", color=discord.Color.gold())
    embed.add_field(name="🔧 General", value="`/list` → Show this menu\n`/san_set` → Set log channel\n`/invite` → Get bot invite\n`/rules` → Read rules", inline=False)
    embed.add_field(name="🛡️ Protection", value="`/on` → Activate Lockdown\n`/off` → Disable Lockdown", inline=False)
    embed.add_field(name="👑 Moderation", value="`/remove_timeout` `/ban` `/kick` `/timeout`", inline=False)
    embed.set_footer(text="Only Bot King + Owner can use admin commands | /san_op is secret")
    await interaction.response.send_message(embed=embed)

@tree.command(name="san_set", description="Set current channel as Security Log Channel")
async def san_set(interaction: discord.Interaction):
    if not has_permission(interaction.user, interaction.guild):
        return await interaction.response.send_message("❌ No permission!", ephemeral=True)
    config["notification_channel"] = str(interaction.channel_id)
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f)
    await interaction.response.send_message(f"✅ Log channel set to {interaction.channel.mention}", ephemeral=False)

@tree.command(name="invite", description="Get bot invite link in DM")
async def invite(interaction: discord.Interaction):
    invite_link = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=8"
    try:
        await interaction.user.send(f"🔗 Invite Link:\n{invite_link}")
        await interaction.response.send_message("✅ Invite link sent to DM!", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Could not send DM.", ephemeral=True)

@tree.command(name="rules", description="Show server rules in your DM")
async def rules(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Server Rules", color=discord.Color.blue())
    embed.description = "• No spam or flooding\n• No profanity\n• No raiding\n• Respect everyone\n\nProtected by DevExe Alliance"
    try:
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("✅ Rules sent to your DM!", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Could not send DM.", ephemeral=True)

# ====================== RUN ======================
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Token not found!")
    else:
        bot.run(token)
