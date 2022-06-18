import logging
import os

import discord
from discord.ext import commands

from config import config
from injectors import connections
from models.colors import TextColors
from models.exceptions import BotException

config = config.discord
tc = TextColors()
dis_logger = logging.getLogger('discord')
dis_logger.setLevel(logging.ERROR)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s]: %(message)s',
    datefmt='%H:%M:%S'
)

bot = commands.Bot(
    command_prefix=config.prefix,

)


async def send_embed(ctx: commands.Context, msg: str, *,
                     title: str = None,
                     color: discord.Colour = discord.Colour.blue(),
                     url: str = None,
                     img: str = None):
    embed = discord.Embed()
    if title:
        embed.title = title
    embed.description = msg
    embed.colour = color
    if url:
        embed.url = url
    if img:
        embed.set_image(url=img)
    if len(embed) >= 6000:
        await ctx.send(embed=discord.Embed(
            discription='Message overflow', colour=discord.Colour.red()))
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    logging.info('initializing db')
    connections.init_db()
    if not os.path.exists('../music'):
        os.mkdir('../music')
    logging.info(f'{tc.green}Ready!{tc.end}')


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        await send_embed(
            ctx, f'Command not found, use {bot.command_prefix}help.',
            color=discord.Colour.red())
    elif isinstance(error, commands.MissingRequiredArgument):
        await send_embed(ctx, f"""
            Missing command parameter.
            Missing parameter: **error.param**
            Use **{ctx.command}help {ctx.command}** to get help.
            """, color=discord.Colour.red())
    elif isinstance(error, commands.NotOwner):
        await ctx.send(f"Error: {error}")
    elif isinstance(error, BotException):
        await send_embed(ctx, error.msg, color=discord.Colour.red())
    else:
        img_url = 'https://i.ibb.co/Pc7W8k9/index.jpg'
        await send_embed(ctx,
                         f'{ctx.author.nick},',
                         color=discord.Colour.red(),
                         img=img_url
                         )
        logging.error(
            f'''{tc.bold}{tc.header}Error occurred{tc.end}
            {tc.bold}{tc.underline}Command:{tc.end} {ctx.command}
            {tc.bold}{tc.underline}Error log:{tc.end}
            {tc.red}{error}{tc.end}''')


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')
        logging.info(f'Module {filename[:-3]} loaded')

logging.info('Connecting to gateway')

if __name__ == '__main__':
    bot.run(config.token)
