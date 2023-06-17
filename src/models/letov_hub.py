import dataclasses as dc

import sqlalchemy as sa

from .orm import BaseOrm


@dc.dataclass
class LetovHubSession(BaseOrm):
    __tablename__ = 'sessions'
    __table_args__ = {'schema': 'misc'}

    sid: str = dc.field(metadata={
        'sa': sa.Column(sa.VARCHAR(128), primary_key=True, unique=True)
    })
    user: str = dc.field(metadata={
        'sa': sa.Column(sa.TEXT)
    })
    user_id: int = dc.field(metadata={
        'sa': sa.Column(sa.BIGINT)
    })
    guild: int = dc.field(metadata={
        'sa': sa.Column(sa.BIGINT)
    })
    access: int = dc.field(default=0, metadata={
        'sa': sa.Column(sa.Integer)
    })


BaseOrm.REGISTRY.mapped(LetovHubSession)
