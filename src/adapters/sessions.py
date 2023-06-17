import logging

from sqlalchemy.exc import IntegrityError

from injectors.connections import acquire_session
from models.letov_hub import LetovHubSession


class SessionAdapter:

    def __init__(self):
        self.pg = acquire_session()

    def create_session(self, session: LetovHubSession):
        try:
            self.pg.add(session)
            self.pg.commit()
        except IntegrityError as e:
            self.pg.rollback()
            logging.error(f"Error during creating session -> {e}")
            raise

        return session
