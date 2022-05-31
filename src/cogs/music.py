import os.path

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

    def get_song(self, ident: str | int) -> Song:
        return self.pg.execute(sa.select(Song).where(Song.id == ident)).scalar_one_or_none()

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    @commands.command()
    async def list(self, ctx: commands.Context):
        songs = self.pg.execute(sa.select(Song)).scalars().all()
        await ctx.send(songs)

    @commands.command()
    async def play(self, ctx: commands.Context, ident: int):
        status = get(self.bot.voice_clients, guild=ctx.guild)
        try:
            if not status:
                await ctx.author.voice.channel.connect()
        except AttributeError:
            await ctx.send(self.format_message('Connect to a voice channel before playing.'))
            return

        ffmpeg_opts = {}

        def after_play(_):
            print('Done')

        song = self.get_song(ident)

        ctx.voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source=os.path.join('../music', song.filename) or song.url, **ffmpeg_opts
                ), self._music_volume), after=after_play)


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
