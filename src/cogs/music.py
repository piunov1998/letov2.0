import os.path
from asyncio import run_coroutine_threadsafe, CancelledError

import discord
import sqlalchemy as sa
from discord.ext import commands
from discord.utils import get

from injectors.connections import acquire_session
from models.music import Song


class Music(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot
        self.pg = acquire_session()
        self._music_volume = 0.06

    @classmethod
    def format_message(cls, msg, **_):
        return f'```{msg}```'

    @classmethod
    async def send_embed(cls, ctx: commands.Context, msg: str, *,
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
        await ctx.send(embed=embed)

    def get_song(self, ident: str | int) -> Song:
        return self.pg.execute(
            sa.select(Song).where(Song.id == ident)).scalar_one_or_none()

    @classmethod
    async def disconnect(cls, ctx: commands.Context):
        await ctx.voice_client.disconnect()

    @commands.command()
    async def list(self, ctx: commands.Context):
        songs = self.pg.execute(sa.select(Song)).scalars().all()
        description = ''
        for i, song in enumerate(songs):
            description += f'{i + 1}. {song.name}\n'
        await self.send_embed(
            ctx, description,
            title='Song list',
            color=discord.Colour.from_rgb(7, 133, 70)
        )

    @commands.command()
    async def stop(self, ctx: commands.Context):
        try:
            await self.disconnect(ctx)
        except AttributeError:
            await ctx.send(self.format_message('Nothing to stop'))

    @commands.command()
    async def play(self, ctx: commands.Context, ident: int):
        status = get(self.bot.voice_clients, guild=ctx.guild)
        try:
            if not status:
                await ctx.author.voice.channel.connect()
        except AttributeError:
            await ctx.send(self.format_message(
                'Connect to a voice channel before playing.'))
            return

        ffmpeg_opts = {}

        def after_play(error):
            if error:
                print(error)
            vc = get(self.bot.voice_clients, guild=ctx.guild)
            if not vc:
                return
            future = run_coroutine_threadsafe(
                self.disconnect(ctx), self.bot.loop)
            try:
                future.result()
            except CancelledError:
                print('Pizda')

        song = self.get_song(ident)
        source = os.path.join('../music', song.filename) or song.url

        ctx.voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source, **ffmpeg_opts
                ), self._music_volume), after=after_play)


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
