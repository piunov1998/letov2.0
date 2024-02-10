import dataclasses as dc
import re

import yt_dlp.utils
from youtube_search import YoutubeSearch
from yt_dlp import YoutubeDL

from models import exceptions


@dc.dataclass
class MusicInfo:
    """Информация об песни с YT"""

    name: str = dc.field()
    url: str = dc.field()
    channel: str = dc.field()
    audio_source: str | None = dc.field(default="")
    duration: str = dc.field(default="0:00")


class YouTubeAdapter:

    @staticmethod
    def validate_url(url, safe: bool = False) -> bool:
        exp = re.compile(r'https?://(?:www\.)?youtu(?:\.be|be\.com)/\S+')
        if not re.fullmatch(exp, url):
            if safe:
                return False
            raise exceptions.WrongURL('Invalid URL was given')

        return True

    @staticmethod
    def extract_audio_info(link: str) -> MusicInfo:
        """Получение информации о песне из YT"""

        ydl_opts = {'format': 'bestaudio', 'noplaylist': True}

        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(link, download=False)
            except yt_dlp.utils.DownloadError as e:
                raise exceptions.VideoIsUnavailable(link, e.msg)
            song_format = next(
                f for f in info['formats']
                if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none'
            )

        music_info = MusicInfo(
            name=info['title'],
            url=f'https://youtu.be/{info["id"]}',
            audio_source=song_format['url'],
            channel=info['channel'],
            duration=info['duration'],
        )
        return music_info

    @classmethod
    def search(cls, key: str, limit: int = None) -> list[MusicInfo]:
        """Поиск песен на YT"""

        result = []
        search_results = YoutubeSearch(key, limit)
        for video in search_results.videos:
            result.append(MusicInfo(
                url=f'https://youtu.be/{video["id"]}',
                name=video["title"],
                duration=video["duration"],
                channel=video["channel"]
            ))

        return result
