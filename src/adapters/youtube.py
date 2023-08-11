import dataclasses as dc
import re

from youtube_search import YoutubeSearch
from yt_dlp import YoutubeDL

from models import exceptions


@dc.dataclass
class MusicInfo:
    """Информация об песни с YT"""

    title: str = dc.field()
    url: str = dc.field()
    audio_source: str = dc.field()
    duration: int = dc.field(default=0)


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
            info = ydl.extract_info(link, download=False)
            song_format = next(
                f for f in info['formats']
                if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none'
            )
        title = info['title']
        url = f'https://youtu.be/{info["id"]}'
        audio_source = song_format['url']
        # TODO: добавить больше параметров
        return MusicInfo(title, url, audio_source)

    @classmethod
    def search(cls, key: str, limit: int = None) -> list[MusicInfo]:
        """Поиск песен на YT"""

        result = []
        search_results = YoutubeSearch(key, limit)
        for video in search_results.videos:
            url = f'https://youtu.be/{video["id"]}'
            result.append(cls.extract_audio_info(url))

        return result
