import discord,os
from pprint import pprint 
from dotenv import load_dotenv

load_dotenv()
DISCORD_API_KEY = os.environ.get('DISCORD_API_KEY')




class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        pprint(message)




intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(DISCORD_API_KEY)