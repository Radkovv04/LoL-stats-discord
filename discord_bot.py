# discord_bot.py
import discord
from discord.ext import tasks
import asyncio
import Test_best_stats  # тук импортираш твоя скрипт с анализатора

TOKEN = "MTQyMjc4MDEyMTg2NTEyNTk2OA.GmrV9l.5yGHnUj-YLU0lpuNOvg5P06PXWhz2-mUl97vu0"  # токена на бота
GUILD_ID = 1178426885257052191  # ID на твоя Discord сървър
CHANNEL_IDS = {
     "alek": 1422419648963416117,
     "radko": 1422419236005085275,
     "lubo": 1422419930447609877,
     "zahir": 1422419077460131883,
     "maykal": 1422420186484441119
}

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)  # само Client, не discord.Bot

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    weekly_report.start()  # стартираме задачата

# Задача, която се пуска всяка седмица
@tasks.loop(seconds=604800)
async def weekly_report():
    for summoner in CHANNEL_IDS:
        channel_id = CHANNEL_IDS[summoner]
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        try:
            puuid = Test_best_stats.fetch_puuid(summoner)  # summoner е "alek", "radko", ...
  # използваме твоята функция
            stats, start, end, best, worst, games = Test_best_stats.analyze_weekly_stats(puuid)
            message = f"--- Weekly stats for {summoner} ---\n"
            message += f"From {start.strftime('%d/%m/%Y')} to {end.strftime('%d/%m/%Y')}\n"
            message += f"Games: {stats['games']} | Wins: {stats['wins']} | Losses: {stats['losses']}\n"
            for key in ["KDA","KP","DMG/MIN","Gold/Min","Vision/Min","WardsPlaced","WardsKilled","CtrlWardsBuy","CtrlWardsKill","CS@10","Gold@10","CS@15","Gold@15","Level@10","Level@15"]:
                vals = stats[key]
                if not vals:
                    continue
                avg_val = sum(v if isinstance(v,(int,float)) else 0 for v in vals)/len(vals)
                if key == "KP":
                    message += f"{key}: {round(avg_val,1)}%\n"
                else:
                    message += f"{key}: {round(avg_val,1)}\n"
            await channel.send(f"```{message}```")
        except Exception as e:
            await channel.send(f"Error fetching stats for {summoner}: {e}")

bot.run(TOKEN)
