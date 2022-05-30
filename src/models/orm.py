import dataclasses as dc

from sqlalchemy.orm import registry


@dc.dataclass
class BaseOrm:

    __tablename__ = ''
    __sa_dataclass_metadata_key__ = 'sa'

    REGISTRY = registry()