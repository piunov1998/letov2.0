from datetime import datetime

import psycopg2.errorcodes
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from injectors.connections import acquire_session
from models import exceptions
from models.music import Song, Playback, QueuePos


class MusicAdapter:

    def __init__(self):
        self.pg = acquire_session()

    def get_songs(self, limit: int = 0, order_by=Song.id) -> list[Song]:
        """Получение списка всех песен"""

        query = sa.select(Song).order_by(order_by)

        if limit > 0:
            query = query.limit(limit)

        song = self.pg.execute(query).scalars().all()
        return song

    def get_first_in_queue(self, guild_id: int) -> QueuePos:
        """Получение первой песни в очереди"""

        query = sa.select(QueuePos) \
            .where(QueuePos.guild_id == guild_id) \
            .order_by(QueuePos.id) \
            .limit(1)
        return self.pg.execute(query).scalars().first()

    def get_song_by_id(self, song_id: int) -> Song:
        """Получение песни по ее id"""

        query = sa.select(Song).where(Song.id == song_id)
        song = self.pg.execute(query).scalar_one_or_none()
        return song

    def get_song_by_url(self, url: str) -> Song:
        """Получение песни по url"""

        query = sa.select(Song).where(Song.url == url)
        song = self.pg.execute(query).scalar_one_or_none()
        return song

    def find_songs(
        self,
        key_words: list[str],
        limit: int = 0,
        order_by=Song.id
    ) -> list[Song]:
        """Получение списка песен с ключевыми словами в названии"""

        kw = '%'.join(key_words)
        query = sa.select(Song) \
            .filter(Song.name.ilike(f'%{kw}%')) \
            .order_by(order_by)

        if limit > 0:
            query = query.limit(limit)

        song = self.pg.execute(query).scalars().all()
        return song

    def add_song(self, title: str, url: str) -> Song:
        """Добавление песни в БД"""

        song = Song(name=title, url=url)

        try:
            self.pg.add(song)
            self.pg.commit()
        except IntegrityError as e:
            self.pg.rollback()
            if e.orig.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
                raise exceptions.DuplicateSong
            raise

        return song

    def remove_song(self, song_id: int):
        """Удаление песни из БД"""

        query = sa.delete(Song).where(Song.id == song_id)
        self.pg.execute(query)
        self.pg.commit()

    def get_queue(self, guild_id: int) -> list[QueuePos]:
        """Получение очереди воспроизведения"""

        query = sa.select(QueuePos) \
            .where(QueuePos.guild_id == guild_id) \
            .order_by(QueuePos.id)
        queue = self.pg.execute(query).scalars().all()

        return queue

    def add_to_queue(self, song: Song, guild_id: int) -> QueuePos:
        """Добавление песни в очередь"""

        qp = QueuePos(song, guild_id)
        self.pg.add(qp)
        self.pg.commit()

        return qp

    def get_from_queue(self, position: int) -> QueuePos:
        """Получение песни из очереди"""

        query = sa.select(QueuePos).where(QueuePos.id == position)
        qpos = self.pg.execute(query).scalar_one()

        return qpos

    def del_from_queue(self, position: int):
        """Удаление песни из очереди"""

        query = sa.delete(QueuePos).where(QueuePos.id == position)
        self.pg.execute(query)
        self.pg.commit()

    def clear_queue(self, guild_id: int):
        """Очистка очереди"""

        query = sa.delete(QueuePos).where(QueuePos.guild_id == guild_id)
        self.pg.execute(query)
        self.pg.commit()

    def add_to_history(self, user: str, song_id: int, guild_id: int):
        pb = Playback(song_id, user, guild_id, datetime.now())
        self.pg.add(pb)
        self.pg.commit()
