import os

import discord
from discord.ext import commands

from config import config
from injectors import connections

config = config.discord

bot = commands.Bot(
    command_prefix=config.prefix,

)


async def send_embed(ctx: commands.Context, msg: str, *,
                     title: str = None,
                     color: discord.Colour = discord.Colour.blue(),
                     url: str = None):
    embed = discord.Embed()
    if title:
        embed.title = title
    embed.description = msg
    embed.colour = color
    if url:
        embed.url = url
    if len(embed) >= 6000:
        await ctx.send(embed=discord.Embed(
            discription='Message overflow', colour=discord.Colour.red()))
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print('initializing db')
    connections.init_db()
    if not os.path.exists('../music'):
        os.mkdir('../music')
    print('Ready!')


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
    else:
        await send_embed(ctx,
                         f'{ctx.author.nick}, idi nahui',
                         color=discord.Colour.red()
                         )
        print(f"""
            Command: {ctx.command}
            Error log:
            {error}""")


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')
        print(f'Module {filename[:-3]} loaded')

print('Connecting to gateway...')

if __name__ == '__main__':
    bot.run(config.token)
