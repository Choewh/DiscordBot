import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Load the forbidden word game cog
async def load_extensions():
    await bot.load_extension('forbidden_word_game')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await load_extensions()

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 