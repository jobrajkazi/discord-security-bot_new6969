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
tree = app_commands.CommandTree(bot)

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

# Profanity Patterns
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

# ====================== PERMISSION CHECK ======================
def has_permission(member, guild):
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
    # Create Bot King Role
    if not discord.utils.get(guild.roles, name="Bot King"):
        await guild.create_role(name="Bot King", color=discord.Color.gold(), permissions=discord.Permissions(administrator=True))
    
    # Create Security Admin Role
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
    if not has_permission(message.author, message.guild):
        await check_spam(message)
        await check_content(message)

# ====================== SLASH COMMAND ======================
@tree.command(name="san_set", description="Set current channel as Security Bot Log Channel")
async def san_set(interaction: discord.Interaction):
    if not has_permission(interaction.user, interaction.guild):
        return await interaction.response.send_message("❌ No permission!", ephemeral=True)
    config["notification_channel"] = str(interaction.channel_id)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    await interaction.response.send_message(f"✅ Log channel set to {interaction.channel.mention}", ephemeral=False)

# ====================== !LIST COMMAND ======================
@bot.command(name='list')
async def list_commands(ctx):
    embed = discord.Embed(
        title="🔰 Security Bot - All Commands",
        description="Here are all available commands:",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🔧 Setup Commands",
        value="`!setup` → Create control panel\n"
              "`/san_set` → Set log channel (recommended)\n"
              "`!list` → Show this message",
        inline=False
    )
    
    embed.add_field(
        name="👑 Admin Commands (Bot King / Owner)",
        value="`!addadmin @user` → Add bot admin\n"
              "`!removeadmin @user` → Remove bot admin\n"
              "`!unban <user_id>` → Unban user\n"
              "`!ban @user` → Ban user (add this if needed)",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Auto Moderation",
        value="• Auto detects spam & profanity\n"
              "• Auto timeout/kick on violation\n"
              "• Immune to Bot King & Admins",
        inline=False
    )
    
    embed.set_footer(text="Only Bot King role + Server Owner have full access")
    await ctx.send(embed=embed)

# ====================== OTHER FUNCTIONS ======================
async def check_spam(message):
    user_id = str(message.author.id)
    current_time = datetime.datetime.now().timestamp()
    if user_id not in spam_tracker:
        spam_tracker[user_id] = []
    spam_tracker[user_id].append(current_time)
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if current_time - t <= config["spam_timeframe"]]
    
    if len(spam_tracker[user_id]) > config["spam_threshold"]:
        await punish_user(message.author, message.guild, "spam", message.channel)
        await notify_admins(message.guild, f"🚨 Spam → {message.author.mention}")

async def check_content(message):
    content = message.content.lower()
    for pattern in profanity_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            await punish_user(message.author, message.guild, "profanity", message.channel)
            await notify_admins(message.guild, f"🚨 Profanity → {message.author.mention}")
            await message.delete()
            break

async def punish_user(user, guild, violation_type, channel):
    try:
        if violation_type == "timeout":
            await user.timeout(datetime.timedelta(seconds=config["timeout_duration"]))
        elif violation_type == "kick":
            await user.kick(reason=f"Auto {violation_type}")
        elif violation_type == "ban":
            await user.ban(reason=f"Auto {violation_type}")
    except:
        pass

async def notify_admins(guild, message):
    if config.get("notification_channel"):
        ch = bot.get_channel(int(config["notification_channel"]))
        if ch:
            await ch.send(message)

async def setup_control_panel(guild):
    pass  # You can expand later

# ====================== RUN ======================
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found!")
    else:
        bot.run(token)
