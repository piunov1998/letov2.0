import os

from discord.ext import commands

from config import config
from injectors import connections

config = config.discord

bot = commands.Bot(
    command_prefix=config.prefix,

)


@bot.event
async def on_ready():
    connections.init_db()
    if not os.path.exists('../music'):
        os.mkdir('../music')
    print('Ready!')


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')
        print(f'Module {filename[:-3]} loaded')

print('Connecting to gateway...')

if __name__ == '__main__':
    bot.run(config.token)
