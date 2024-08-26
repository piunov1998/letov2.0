import asyncio
import enum
import math
from asyncio import run_coroutine_threadsafe, CancelledError
from typing import Iterable

import discord
import discord.ui
from discord.ext import commands
from discord.utils import get

from adapters import YouTubeAdapter, MusicAdapter
from adapters.youtube import MusicInfo
from models import exceptions
from models.music import Song, QueuePos

MUSIC_PATH = '../music'


class QueueActions(str, enum.Enum):
    ADD = 'add'
    DELETE = 'del'
    LIST = 'list'


class Music(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.yt = YouTubeAdapter()
        self.music = MusicAdapter()
        self.bot = bot
        self._music_volume = 0.05

    @property
    def music_volume_exp(self) -> int:
        return (math.pow(self._music_volume, math.exp(-1)) * 100).__trunc__()

    @music_volume_exp.setter
    def music_volume_exp(self, volume: int):
        self._music_volume = \
            math.pow(min(max(0, volume), 100) / 100, math.exp(1))

    @staticmethod
    def is_playing(ctx: commands.Context) -> bool:
        """Проверка идет ли воспроизведение в данный момент"""

        return ctx.voice_client is not None and (
                ctx.voice_client.is_playing() or ctx.voice_client.is_paused()
        )

    @classmethod
    def format_message(cls, msg, **_):
        return f'```{msg}```'

    @classmethod
    async def send_embed(
            cls,
            ctx: commands.Context, msg: str,
            *,
            title: str = None,
            color: discord.Colour = discord.Colour.blue(),
            url: str = None,
            img: str = None
    ):
        embed = discord.Embed()
        if title:
            embed.title = title
        embed.description = msg
        embed.colour = color
        if url:
            embed.url = url
        if img:
            embed.set_image(url=img)
        if len(embed) >= 6000 or len(embed.description) > 4096:
            await ctx.send(
                embed=discord.Embed(
                    description='Message overflow',
                    colour=discord.Colour.red()
                )
            )
        await ctx.send(embed=embed)

    async def get_saved_song(self, ctx: commands.Context, *args: str) -> Song | None:
        """Получение сохраненной песни"""

        if len(args) == 1 and args[0].isnumeric():
            song_id = int(args[0])
            song = self.music.get_song_by_id(song_id)
        elif len(args) == 1 and args[0].startswith('http'):
            url = args[0]
            song = self.music.get_song_by_url(url)
        else:
            key_words = list(args)
            songs = self.music.find_songs(key_words, 24)
            if len(songs) == 0:
                song = None
            elif len(songs) == 1:
                song = songs[0]
            else:
                song = await self.select_saved_song(ctx, songs, key_words)

        return song

    async def select_saved_song(
            self,
            ctx: commands.Context,
            songs: list[Song],
            match: list[str] = None
    ) -> Song:
        """Выбор песни через UI"""

        song_list: dict[str, Song | None] = {'chosen_song': None}
        event = asyncio.Event()

        rows = []
        select = discord.ui.Select(placeholder="Select song")

        for i, song in enumerate(songs):
            row = song.name
            if match:
                for word in match:
                    row = row.replace(word, f"__**{word}**__")
            rows.append(f"{i + 1}. {row}")
            select.add_option(label=song.name, value=str(song.id))

        async def callback(interaction: discord.Interaction):
            await interaction.message.delete()
            response: discord.InteractionResponse = interaction.response  # type: ignore
            song_id = interaction.data['values'][0]
            song_list['chosen_song'] = self.music.get_song_by_id(song_id)
            response.is_done()
            event.set()

        select.callback = callback

        view = discord.ui.View(timeout=30)
        view.add_item(select)

        msg = '\n'.join(rows)
        msg = await ctx.send(msg, view=view)

        async def timeout():
            await msg.delete()

        view.on_timeout = timeout

        await event.wait()
        view.stop()

        return song_list['chosen_song']

    async def select_song_from_search(
            self,
            ctx: commands.Context,
            songs: list[MusicInfo],
            match: Iterable[str] = None
    ) -> MusicInfo:
        """Выбор песни в поиске через UI"""

        song_list: dict[str, MusicInfo | None] = {'chosen_song': None}
        event = asyncio.Event()

        rows = []
        select = discord.ui.Select(placeholder="Select song")

        for i, song in enumerate(songs):
            song: MusicInfo
            row = song.name
            if match:
                for word in match:
                    row = row.replace(word, f"__**{word}**__")
            rows.append(f"{i + 1}. {row} (@{song.channel}) - {song.duration}")
            select.add_option(label=f"{i + 1}. {song.name} (@{song.channel})", value=str(i))

        async def callback(interaction: discord.Interaction):
            await interaction.message.delete()
            response: discord.InteractionResponse = interaction.response  # type: ignore
            song_id = int(interaction.data['values'][0])
            song_list['chosen_song'] = songs[song_id]
            response.is_done()
            event.set()

        select.callback = callback

        view = discord.ui.View(timeout=30)
        view.add_item(select)

        msg = '\n'.join(rows)
        msg = await ctx.send(msg, view=view)

        async def timeout():
            await msg.delete()

        view.on_timeout = timeout

        await event.wait()
        view.stop()

        return song_list['chosen_song']

    async def connect(self, ctx: commands.Context):
        status = get(self.bot.voice_clients, guild=ctx.guild)
        if not status:
            await ctx.author.voice.channel.connect()

    @classmethod
    async def disconnect(cls, ctx: commands.Context):
        await ctx.voice_client.disconnect(force=False)

    @commands.command()
    async def add(self, ctx: commands.Context, *args: str) -> Song | None:
        """Добавление песни"""

        args_str = ' '.join(args)

        if self.yt.validate_url(args_str, safe=True):
            music_info = self.yt.extract_audio_info(args_str)
        else:
            await self.send_embed(
                ctx, f'Searching **{args_str}** on YouTube...', color=discord.Colour.yellow())
            search_result = self.yt.search(args_str, 5)
            music_info = await self.select_song_from_search(ctx, search_result, args)

        try:
            song = self.music.add_song(music_info.name, music_info.url)
        except exceptions.DuplicateSong as e:
            await self.send_embed(ctx, str(e), color=discord.Colour.red())
            return None
        await self.send_embed(
            ctx, f'Added **{song.name}**', color=discord.Colour.green())

        return song

    @commands.command()
    async def remove(self, ctx: commands.Context, song_id: str):
        """Удаление песни"""

        if not song_id.isnumeric():
            await self.send_embed(
                ctx, 'Incorrect argument', color=discord.Colour.red())
            return

        song = self.music.get_song_by_id(int(song_id))
        self.music.remove_song(song.id)

        await self.send_embed(
            ctx, f'**{song.name} has been removed**',
            color=discord.Colour.green()
        )

    @commands.command()
    async def list(self, ctx: commands.Context, *args: str):
        """Получение всего списка песен или по ключевым словам"""

        if args:
            key_words = list(args)
            songs = self.music.find_songs(key_words, order_by=Song.name)
        else:
            songs = self.music.get_songs()

        title = 'Song list'
        description = ''

        for song in songs:
            row = f'( **{song.id}** )  {song.name}\n'
            if len(description + row) < 4000:
                description += row
                continue
            else:
                await self.send_embed(
                    ctx, description,
                    title=title,
                    color=discord.Colour.from_rgb(7, 133, 70)
                )
                description = row
            title = None
        await self.send_embed(
            ctx, description,
            title=title,
            color=discord.Colour.from_rgb(7, 133, 70)
        )

    @commands.command(brief='Cancel playback')
    async def stop(self, ctx: commands.Context):
        try:
            await self.disconnect(ctx)
        except AttributeError:
            await self.send_embed(
                ctx, 'Nothing to stop', color=discord.Colour.red()
            )

    @commands.command(brief='Pauses playback.')
    async def pause(self, ctx: commands.Context):
        """Pauses current playback."""
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        else:
            await self.send_embed(
                ctx, 'Nothing is playing.', color=discord.Colour.red()
            )

    @commands.command(brief='Resumes playback')
    async def resume(self, ctx: commands.Context):
        """Resumes playback if it was paused."""
        if ctx.voice_client is not None and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
        else:
            await self.send_embed(
                ctx, 'Nothing is paused', color=discord.Colour.red()
            )

    @commands.command(name='play')
    async def play(self, ctx: commands.Context, *args: str):
        """Проигрывание музыки"""

        is_playing = self.is_playing(ctx)

        if args:
            if not is_playing:
                self.music.clear_queue(ctx.guild.id)

            await self.queue(ctx, QueueActions.ADD, *args)

        if is_playing:
            return

        q = self.music.get_first_in_queue(ctx.guild.id)

        if q is None:
            await self.send_embed(
                ctx, "Nothing to play ¯\\_(ツ)_/¯", color=discord.Colour.red()
            )
            return

        try:
            await self.connect(ctx)
        except AttributeError:
            await self.send_embed(
                ctx, 'Connect to a voice channel before playing.',
                color=discord.Colour.red())
            return

        await self.player(ctx, q)

    async def player(self, ctx: commands.Context, queue_pos: QueuePos):

        def after_play(error):
            self.music.del_from_queue(queue_pos.id)

            if error:
                print(error)
                return
            vc = get(self.bot.voice_clients, guild=ctx.guild)
            if not vc:
                return

            q = self.music.get_first_in_queue(ctx.guild.id)
            if q is None:
                coro = self.disconnect(ctx)
            else:
                coro = self.player(ctx, q)
            future = run_coroutine_threadsafe(
                coro, self.bot.loop)
            try:
                future.result(10)
            except CancelledError:
                print('Pizda')

        try:
            source = self.yt.extract_audio_info(queue_pos.song.url).audio_source
        except Exception:
            await self.stop(ctx)
            raise
        ffmpeg_opts = {
            'before_options': '-analyzeduration 0 '
                              '-re '
                              '-reconnect 1 '
                              '-reconnect_streamed 1 '
                              '-reconnect_delay_max 5 '
                              '-http-proxy http://proxy:8080 ',
            'options': '-vn '
                       '-bufsize 64k '
        }

        await self.send_embed(ctx, f'Playing **{queue_pos.song.name}**')
        self.music.add_to_history(
            ctx.author.nick, queue_pos.song.id, ctx.guild.id
        )

        ctx.voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source, **ffmpeg_opts
                ), self._music_volume), after=after_play)

    @commands.command(aliases=['v'])
    async def volume(self, ctx: commands.Context, volume: str = None):
        """Управление громкостью воспроизведения"""

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
        if self.is_playing(ctx):
            ctx.voice_client.source.volume = self._music_volume

    @commands.command(aliases=['q'])
    async def queue(
            self,
            ctx: commands.Context,
            act: QueueActions = QueueActions.LIST,
            *args: str
    ):
        """Управление очередь воспроизведения"""

        match act:

            case QueueActions.ADD:
                song = await self.get_saved_song(ctx, *args) or await self.add(ctx, *args)
                self.music.add_to_queue(song, ctx.guild.id)
                await self.send_embed(ctx, f'**{song.name}** added to queue')

            case QueueActions.DELETE:
                if not (len(args) == 1 and args[0].isnumeric()):
                    await self.send_embed(
                        ctx, 'This is not id', color=discord.Colour.red())
                    return
                queue_pos = int(args[0]) - 1
                queue = self.music.get_queue(ctx.guild.id)
                q = queue[queue_pos]
                song_name = q.song.name
                self.music.del_from_queue(q.id)
                await self.send_embed(
                    ctx, f'**{song_name}** removed from queue'
                )

            case QueueActions.LIST:
                queue = self.music.get_queue(ctx.guild.id)
                msg = ''
                for i, pos in enumerate(queue):
                    msg += f'{i + 1: >{len(str(len(queue)))}}.  {pos.song.name}\n'
                await self.send_embed(ctx, msg, title='Queue')


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
