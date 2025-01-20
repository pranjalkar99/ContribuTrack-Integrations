import discord, os
from discord.ext import commands
from dotenv import load_dotenv
import logging
import logging.handlers
import aiosqlite  # Changed from psycopg2 to aiosqlite

# Set up logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load environment variables
load_dotenv()
DISCORD_API_KEY = os.environ.get('DISCORD_API_KEY')

if not DISCORD_API_KEY:
    print("DISCORD_API_KEY not found! Check your .env file.")
    exit(1)

# Intents for the bot
intents = discord.Intents.default()
intents.message_content = True

# Bot class with aiosqlite
class SaaSBot(discord.Client):
    def __init__(self, db_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_file = db_file

    async def on_ready(self):
        print(f'Logged on as {self.user}')
        # Initialize the database connection
        self.db = await aiosqlite.connect(self.db_file)
        self.cursor = await self.db.cursor()

        # Ensure the tables exist
        await self.init_database()

    async def init_database(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER REFERENCES servers(id),
                discord_channel_id TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_user_id TEXT NOT NULL UNIQUE,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER REFERENCES channels(id),
                user_id INTEGER REFERENCES users(id),
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL, 
            attachment_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            url TEXT NOT NULL,
            content_type TEXT,
            size INTEGER,
            height INTEGER,
            width INTEGER,
            description TEXT,
            ephemeral BOOLEAN,
            duration FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages(id)
            );
            """
        ]
        for query in queries:
            await self.cursor.execute(query)
        await self.db.commit()

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Identify the server (e.g., by environment or config)
        server_id = await self.get_server_id(message.guild.id)

        # Store the channel if it doesn't exist
        channel_id = await self.get_or_create_channel(server_id, message.channel.id, message.channel.name)

        # Store the user if it doesn't exist
        user_id = await self.get_or_create_user(message.author.id, message.author.name)

        
        # Store the message
        message_id = await self.store_message(channel_id, user_id, message.content)

        if message.attachments:
            for attachment in message.attachments:
                await self.store_attachment(message_id, attachment.id, attachment.filename, attachment.url, attachment.content_type, attachment.size, attachment.height, attachment.width, attachment.description, attachment.ephemeral, attachment.duration)

        print(f'Message from {message.author} in {message.channel.name}: {message.content}')


        print(f'Message from {message.author} in {message.channel.name}: {message.content}')


    async def store_attachment(self, message_id, attachment_id, filename, url, content_type, size, height, width, description, ephemeral, duration):
        # Store attachment details in the attachments table
        await self.cursor.execute(
            """
            INSERT INTO attachments (message_id, attachment_id, filename, url, content_type, size, height, width, description, ephemeral, duration) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                attachment_id, filename, url, content_type, size, height, width, description, ephemeral, duration
            )
        )
        await self.db.commit()

    async def get_server_id(self, discord_guild_id):
        # Placeholder logic; in a real app, map Discord guild IDs to servers
        await self.cursor.execute("SELECT id FROM servers WHERE name = ?", (f"server-{discord_guild_id}",))
        result = await self.cursor.fetchone()
        if not result:
            # Create a new server
            await self.cursor.execute("INSERT INTO servers (name) VALUES (?)", (f"server-{discord_guild_id}",))
            
            await self.db.commit()
            server_id = self.cursor.lastrowid
        else:
            server_id = result[0]
        return server_id

    async def get_or_create_channel(self, server_id, discord_channel_id, name):
        await self.cursor.execute("SELECT id FROM channels WHERE discord_channel_id = ?", (str(discord_channel_id),))
        result = await self.cursor.fetchone()
        if not result:
            # Create a new channel
            await self.cursor.execute(
                "INSERT INTO channels (server_id, discord_channel_id, name) VALUES (?, ?, ?)",
                (server_id, str(discord_channel_id), name)
            )
            channel_id = self.cursor.lastrowid
            await self.db.commit()
        else:
            channel_id = result[0]
        return channel_id

    async def get_or_create_user(self, discord_user_id, name):
        await self.cursor.execute("SELECT id FROM users WHERE discord_user_id = ?", (str(discord_user_id),))
        result = await self.cursor.fetchone()
        if not result:
            # Create a new user
            await self.cursor.execute(
                "INSERT INTO users (discord_user_id, name) VALUES (?, ?)",
                (str(discord_user_id), name)
            )
            user_id = self.cursor.lastrowid
            await self.db.commit()
        else:
            user_id = result[0]
        return user_id

    async def store_message(self, channel_id, user_id, content):
        await self.cursor.execute(
            "INSERT INTO messages (channel_id, user_id, content) VALUES (?, ?, ?)",
            (channel_id, user_id, content)
        )
        await self.db.commit()
        return self.cursor.lastrowid

    async def close(self):
        if hasattr(self, 'db') and self.db:
            await self.db.close()
        await super().close()

# Database configuration (use a SQLite file)
db_file = 'saas_db.sqlite'  # SQLite file to store your data

client = SaaSBot(db_file, intents=intents)
client.run(DISCORD_API_KEY)
