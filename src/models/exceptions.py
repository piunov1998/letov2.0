import dataclasses as dc


@dc.dataclass
class BotException(Exception):
    """Base bot exception"""

    msg: str = dc.field(default='error')


class WrongURL(BotException):
    """URL validation error"""
