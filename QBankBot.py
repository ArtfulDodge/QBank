#QBankBot.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from exceptions import *

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix='q!')

@bot.event
async def on_ready():
	print(f'{bot.user} has connected to Discord!')

bot.run(TOKEN)