import logging
import logging.handlers
import os
from pprint import pprint

import discord
from dotenv import load_dotenv

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
logging.getLogger("discord.http").setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename="discord.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


load_dotenv()
DISCORD_API_KEY = os.environ.get("DISCORD_API_KEY")


class MyClient(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content == "ping":
            await message.channel.send("pong")

        print(f"Message from {message.author}: {message.content}")
        pprint(message)


intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)

# bot = commands.Bot(command_prefix='>', intents=intents)

# @bot.command()
# async def ping(ctx):
#     await ctx.send('pong')

# bot.run(DISCORD_API_KEY)

client.run(DISCORD_API_KEY)
