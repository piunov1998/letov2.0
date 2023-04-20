import dataclasses as dc
import re

from youtube_search import YoutubeSearch
from yt_dlp import YoutubeDL

from models import exceptions


@dc.dataclass
class AudioInfo:
    """Информация об песни с YT"""

    title: str = dc.field()
    url: str = dc.field()
    duration: int = dc.field(default=0)


class YouTubeAdapter:

    @staticmethod
    def validate_url(url):
        if not re.fullmatch(r'https?://(?:www\.)?youtu(?:\.be|be\.com)/\S+', url):
            raise exceptions.WrongURL('Invalid URL was given')

    @staticmethod
    def extract_audio_info(link: str) -> AudioInfo:
        """Получение информации о песне из YT"""

        ydl_opts = {'format': 'bestaudio', 'noplaylist': True}

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            song_format = next(
                f for f in info['formats']
                if f['acodec'] != 'none' and f['vcodec'] == 'none'
            )
        title = info['title']
        url = song_format['url']
        # TODO: добавить больше параметров
        return AudioInfo(title, url)

    @classmethod
    def search(cls, key: str, limit: int = None) -> list[AudioInfo]:
        """Поиск песен на YT"""

        result = []
        search_results = YoutubeSearch(key, limit)
        for video in search_results:
            url = f'https://youtu.be/{video["id"]}'
            result.append(cls.extract_audio_info(url))

        return result
