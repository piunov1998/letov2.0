import math
import os.path
from asyncio import run_coroutine_threadsafe, CancelledError
from datetime import datetime

import discord
import psycopg2.errorcodes
import sqlalchemy as sa
from discord.ext import commands
from discord.utils import get
from sqlalchemy.exc import IntegrityError
from youtube_search import YoutubeSearch
from yt_dlp import YoutubeDL

from injectors.connections import acquire_session
from models.music import Song, Playback, QueuePos

MUSIC_PATH = '../music'


class Music(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.pg = acquire_session()
        self.bot = bot
        self._music_volume = 0.05

    @property
    def music_volume_exp(self) -> int:
        return (math.pow(self._music_volume, math.exp(-1)) * 100).__trunc__()

    @music_volume_exp.setter
    def music_volume_exp(self, volume: int):
        self._music_volume = \
            math.pow(min(max(0, volume), 100) / 100, math.exp(1))

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
        if len(embed) >= 6000:
            await ctx.send(embed=discord.Embed(
                discription='Message overflow', colour=discord.Colour.red()))
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

    def get_first_in_queue(self) -> QueuePos:
        return self.pg.execute(
            sa.select(QueuePos).order_by(QueuePos.id)).scalars().first()  # noqa

    def get_song_db(self, *args: str) -> Song:

        if len(args) == 1 and args[0].isnumeric():
            song = self.pg.execute(
                sa.select(Song).where(Song.id == args[0])).scalar_one_or_none()
        elif len(args) == 1 and args[0].startswith('http'):
            song = self.pg.execute(
                sa.select(Song).where(Song.url == args[0])).scalar_one_or_none()
        else:
            kw = '%'.join(args)
            song = self.pg.execute(
                sa.select(Song).filter(
                    Song.name.ilike(f'%{kw}%'))).scalars().first()  # noqa

        return song

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

    def log(self, user: str, song_id: int):
        pb = Playback(song_id, user, datetime.now())
        self.pg.add(pb)
        self.pg.commit()

    async def connect(self, ctx: commands.Context):
        status = get(self.bot.voice_clients, guild=ctx.guild)
        if not status:
            await ctx.author.voice.channel.connect()

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
        with self.pg:
            try:
                self.pg.add(song)
                self.pg.commit()
            except IntegrityError as e:
                if e.orig.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
                    self.pg.rollback()
                    await self.send_embed(
                        ctx, 'Song with this source is already in database',
                        color=discord.Colour.red())
                    return self.get_song_db(*args)
                raise
        await self.send_embed(
            ctx, f'Added **{song.name}**', color=discord.Colour.blurple())
        return song

    @commands.command()
    async def remove(self, ctx: commands.Context, song_id: str):
        if not song_id.isnumeric():
            await self.send_embed(
                ctx, 'Incorrect argument', color=discord.Colour.red())
            return
        song = self.pg.execute(
            sa.select(Song).where(Song.id == int(song_id))).scalar_one_or_none()
        self.pg.delete(song)
        self.pg.commit()

    @commands.command()
    async def list(self, ctx: commands.Context, *args: str):
        if args:
            kw = '%'.join(args)
            query = sa.select(Song).filter(
                Song.name.ilike(f'%{kw}%')).order_by(Song.name)  # noqa
        else:
            query = sa.select(Song).order_by(Song.id)
        songs = self.pg.execute(query).scalars().all()
        description = ''
        for song in songs:
            description += f'{song.id}. {song.name}\n'
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

    @commands.command(name='play')
    async def play(self, ctx: commands.Context, *args: str):

        if args:
            self.pg.execute('TRUNCATE music.queue;')
            self.pg.commit()
            await self.queue(ctx, 'add', *args)
        q = self.get_first_in_queue()
        await self.player(ctx, q.song)

    async def player(self, ctx: commands.Context, song: Song = None):

        def after_play(error):
            self.pg.delete(self.get_first_in_queue())
            self.pg.commit()

            if error:
                print(error)
                return
            vc = get(self.bot.voice_clients, guild=ctx.guild)
            if not vc:
                return

            q = self.get_first_in_queue()
            if q is None:
                coro = self.disconnect(ctx)
            else:
                coro = self.player(ctx, q.song)
            future = run_coroutine_threadsafe(
                coro, self.bot.loop)
            try:
                future.result(10)
            except CancelledError:
                print('Pizda')

        if song.filename:
            source = os.path.join(MUSIC_PATH, song.filename)
            ffmpeg_opts = {}
        elif song.url:
            _, source = self.get_audio_url(song.url)
            ffmpeg_opts = {
                'before_options': '-reconnect 1 '
                                  '-reconnect_streamed 1 '
                                  '-reconnect_delay_max 5',
                'options': '-vn'
            }
        else:
            await self.send_embed(
                ctx, 'Source not found', color=discord.Colour.red())
            return

        try:
            await self.connect(ctx)
        except AttributeError:
            await self.send_embed(
                ctx, 'Connect to a voice channel before playing.',
                color=discord.Colour.red())
            return

        await self.send_embed(ctx, f'Playing **{song.name}**')
        self.log(ctx.author.nick, song.id)

        ctx.voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source, **ffmpeg_opts
                ), self._music_volume), after=after_play)

    @commands.command(aliases=['v'])
    async def volume(self, ctx: commands.Context, volume: str = None):
        if volume is None:
            await self.send_embed(
                ctx, f'Current volume is **{self.music_volume_exp}%**')
            return
        if volume.startswith(('+', '-')) and volume[1:].isnumeric():
            match volume[0], volume[1:]:
                case '+', val:
                    self.music_volume_exp += int(val)
                case '-', val:
                    self.music_volume_exp -= int(val)
        elif volume.isnumeric():
            self.music_volume_exp = int(volume)
        else:
            await self.send_embed(
                ctx, 'Incorrect arguments', color=discord.Colour.red())
            return
        await self.send_embed(
            ctx, f'Volume set to **{self.music_volume_exp}%**',
            color=discord.Colour.from_rgb(227, 178, 43))
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            ctx.voice_client.source.volume = self._music_volume

    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context, act: str = None, *args: str):
        match act:
            case 'add':
                song = self.get_song_db(*args)
                if song is None:
                    song = await self.add(ctx, *args)
                self.pg.add(QueuePos(song))
                await self.send_embed(ctx, f'**{song.name}** added to queue')
            case 'del':
                if not (len(args) == 1 and args[0].isnumeric()):
                    await self.send_embed(
                        ctx, 'This is not id', color=discord.Colour.red())
                    return
                q = self.pg.execute(
                    sa.select(
                        QueuePos).where(QueuePos.id == args[0])).scalar_one()
                self.pg.delete(q)
                await self.send_embed(
                    ctx, f'**{q.song.name}** removed from queue')
            case None:
                q = self.pg.execute(sa.select(QueuePos)).scalars().all()
                msg = ''
                for pos in q:
                    msg += f'{pos.id}.  {pos.song.name}\n'
                await self.send_embed(ctx, msg, title='Queue')
        self.pg.commit()


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
