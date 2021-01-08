import typing

if typing.TYPE_CHECKING:
    import qtrio


class SsstError(Exception):
    pass


class InternalError(Exception):
    pass


class QtpyError(SsstError):
    pass


class UnexpectedEmissionError(SsstError):
    def __init__(self, emission: "qtrio.Emission") -> None:
        super().__init__(f"Unexpected emission: {emission!r}")
