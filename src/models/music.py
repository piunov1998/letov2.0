import dataclasses as dc
import typing as t
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import relation

from .orm import BaseOrm


@dc.dataclass
class Song(BaseOrm):
    __tablename__ = 'music'
    __table_args__ = {'schema': 'music'}

    name: str = dc.field(metadata={
        'sa': sa.Column(sa.VARCHAR(128))
    })

    filename: t.Optional[str] = dc.field(default=None, metadata={
        'sa': sa.Column(sa.VARCHAR(64), unique=True)
    })

    url: t.Optional[str] = dc.field(default=None, metadata={
        'sa': sa.Column(sa.VARCHAR(64), unique=True)
    })

    id: t.Optional[int] = dc.field(default=None, metadata={
        'sa': sa.Column(
            sa.Integer, primary_key=True, unique=True, autoincrement=True)
    })


@dc.dataclass
class Playback(BaseOrm):
    __tablename__ = 'history'
    __table_args__ = {'schema': 'music'}

    song: int = dc.field(metadata={
        'sa': sa.Column(
            sa.Integer, sa.ForeignKey(
                'music.music.id', onupdate='CASCADE', ondelete='CASCADE'))
    })

    user: str = dc.field(metadata={
        'sa': sa.Column(sa.VARCHAR(64))
    })

    date: datetime = dc.field(default_factory=datetime, metadata={
        'sa': sa.Column(sa.TIMESTAMP)
    })

    id: t.Optional[int] = dc.field(default=None, metadata={
        'sa': sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    })


@dc.dataclass
class QueuePos(BaseOrm):
    __tablename__ = 'queue'
    __table_args__ = {'schema': 'music'}

    song: Song = dc.field(metadata={
        'sa': relation(lambda: Song)
    })

    song_id: t.Optional[int] = dc.field(default=None, metadata={
        'sa': sa.Column(sa.Integer, sa.ForeignKey(
            'music.music.id', onupdate='CASCADE', ondelete='CASCADE'))
    })

    id: t.Optional[int] = dc.field(default=None, metadata={
        'sa': sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    })

    def __post_init__(self):
        if self.song_id is None:
            self.song_id = self.song.id


BaseOrm.REGISTRY.mapped(Song)
BaseOrm.REGISTRY.mapped(Playback)
BaseOrm.REGISTRY.mapped(QueuePos)
