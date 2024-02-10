class BotException(Exception):
    MESSAGE = "base error"

    @classmethod
    def __str__(cls):
        return cls.MESSAGE


class WrongURL(BotException):
    """URL validation error"""

    MESSAGE = "Wrong URL"


class DuplicateSong(BotException):
    MESSAGE = "Song with this source is already in database"


class VideoIsUnavailable(BotException):

    def __init__(self, url: str = None, extra: str = None):
        self.url = url
        self.extra = extra

    MESSAGE = "Requested song is unavailable"

    def __str__(self):
        msg = self.MESSAGE
        if self.url:
            msg += f" ({self.url})"
        if self.extra:
            msg += f" -> {self.extra}"
        return msg
