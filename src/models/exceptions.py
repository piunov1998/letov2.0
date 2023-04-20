import dataclasses as dc


@dc.dataclass
class BotException(Exception):
    """Base bot exception"""

    msg: str = dc.field(default='error')


class WrongURL(BotException):
    """URL validation error"""


class BaseBotException(Exception):
    MESSAGE = "base error"

    @classmethod
    def __str__(cls):
        return cls.MESSAGE


class DuplicateSong(BaseBotException):
    MESSAGE = "Song with this source is already in database"
