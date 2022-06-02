import os.path
from asyncio import run_coroutine_threadsafe, CancelledError

import discord
import sqlalchemy as sa
from discord.ext import commands
from discord.utils import get
from yt_dlp import YoutubeDL
from youtube_search import YoutubeSearch

from injectors.connections import acquire_session
from models.music import Song

MUSIC_PATH = '../music'


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

    @classmethod
    def get_audio_url(cls, link: str) -> tuple[str, str]:
        ydl_opts = {'format': 'bestaudio'}

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            song_format = next(
                f for f in info['formats']
                if f['acodec'] != 'none' and f['vcodec'] == 'none'
            )
        title = info['title']
        url = song_format['url']
        return title, url

    def get_song_db(self, ident: str | int) -> Song:
        return self.pg.execute(
            sa.select(Song).where(Song.id == ident)).scalar_one_or_none()

    def get_song_yt(self, arg: str) -> tuple[str, str]:
        if arg.startswith('http'):
            url = arg
            title, _ = self.get_audio_url(url)
        else:
            res = YoutubeSearch(arg, 1)
            video = res.videos[0]
            title = video['title']
            url = f'https://www.youtube.com{video["url_suffix"]}'
        return title, url

    @classmethod
    async def disconnect(cls, ctx: commands.Context):
        await ctx.voice_client.disconnect()

    @commands.command()
    async def add(self, ctx: commands.Context, *args) -> Song:
        args = ' '.join(args)
        title, url = self.get_song_yt(args)
        song = Song(
            name=title,
            url=url
        )
        self.pg.add(song)
        self.pg.commit()
        await self.send_embed(
            ctx, f'Added {song.name} ', color=discord.Colour.blurple())
        return song

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

    @commands.command(hidden=True)
    async def test(self, ctx: commands.Context):
        self.get_song_yt('barby girl')

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

        song = self.get_song_db(ident)
        if song.filename:
            source = os.path.join(MUSIC_PATH, song.filename)
            ffmpeg_opts = {}
        elif song.url:
            _, source = self.get_audio_url(song.url)
            ffmpeg_opts = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
        else:
            await self.send_embed(
                ctx, 'Source not found', color=discord.Colour.red())
            return

        ctx.voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source, **ffmpeg_opts
                ), self._music_volume), after=after_play)


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
