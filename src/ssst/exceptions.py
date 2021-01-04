class SsstError(Exception):
    pass


class QtpyError(SsstError):
    pass


class UnexpectedEmissionError(SsstError):
    def __init__(self, emission):
        super().__init__(f"Unexpected emission: {emission!r}")
