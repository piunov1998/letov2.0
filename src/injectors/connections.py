import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, Session

from config import config
from models.orm import BaseOrm
import models.music


def create_engine(db: str = None) -> sa.engine.Engine:

    url = sa.engine.URL.create(
        drivername='postgresql+psycopg2',
        username=config.pg.user,
        password=config.pg.password,
        host=config.pg.host,
        port=config.pg.port,
        database=db or config.pg.database
    )
    return sa.create_engine(url=url, echo=False)


def acquire_session() -> Session:

    session = sessionmaker(bind=create_engine(), autoflush=False)
    session.begin()
    return session()


def init_db():
    engine = create_engine()
    with engine.begin():
        engine.execute('CREATE SCHEMA IF NOT EXISTS music;')
        engine.run_callable(
            BaseOrm.REGISTRY.metadata.create_all
            )
