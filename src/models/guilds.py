import dataclasses as dc

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from .orm import BaseOrm


@dc.dataclass
class Guild(BaseOrm):
    """Модель сервера"""

    __tablename__ = 'guilds'
    __table_args__ = {'schema': 'misc'}

    id: str = dc.field(metadata={
        'sa': sa.Column(sa.VARCHAR(128), primary_key=True)
    })

    settings: dict = dc.field(default_factory=dict, metadata={
        'sa': sa.Column(JSONB)
    })


BaseOrm.REGISTRY.mapped(Guild)
