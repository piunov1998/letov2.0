class TextColors:

    def __init__(self):
        pass

    @property
    def header(self):
        return '\033[47;30m'

    @property
    def bold(self):
        return '\033[1m'

    @property
    def underline(self):
        return '\033[4m'

    @property
    def red(self):
        return '\033[91m'

    @property
    def blue(self):
        return '\033[94m'

    @property
    def cyan(self):
        return '\033[96m'

    @property
    def green(self):
        return '\033[92m'

    @property
    def yellow(self):
        return '\033[93m'

    @property
    def end(self):
        return '\033[0m'
