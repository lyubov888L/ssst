import typing

if typing.TYPE_CHECKING:
    import qtrio


class SsstError(Exception):
    """The base for all SSST errors.  Not to be raised directly, but could be used if
    you want to catch any except this program may explicitly raise."""

    # https://github.com/sphinx-doc/sphinx/issues/7493
    __module__ = "ssst"


class BaseAddressNotFoundError(SsstError):
    """Raised if no address matched the expected SunSpec sentinel value."""

    def __init__(self, addresses: typing.Sequence[int]) -> None:
        import ssst.sunspec

        sentinel = repr(ssst.sunspec.base_address_sentinel)
        addresses = ", ".join(str(address) for address in addresses)
        super().__init__(
            f"SunSpec sentinel {sentinel} not found while searching: {addresses}"
        )

    # https://github.com/sphinx-doc/sphinx/issues/7493
    __module__ = "ssst"


class InternalError(Exception):
    """Raised when things that should not happen do, and they aren't the user's fault."""

    # https://github.com/sphinx-doc/sphinx/issues/7493
    __module__ = "ssst"


class InvalidBaseAddressError(SsstError):
    """Raised if the specified base address does not match the expected SunSpec
    sentinel value.
    """

    def __init__(self, address: int, value: bytes) -> None:
        import ssst.sunspec

        sentinel = repr(ssst.sunspec.base_address_sentinel)
        super().__init__(
            f"SunSpec sentinel {sentinel} not found at {address}: {value!r}"
        )

    # https://github.com/sphinx-doc/sphinx/issues/7493
    __module__ = "ssst"


class QtpyError(SsstError):
    """To be used for any error related to dealing with QtPy that doesn't get a
    dedicated exception type.
    """

    # https://github.com/sphinx-doc/sphinx/issues/7493
    __module__ = "ssst"


class ReuseError(SsstError):
    """Some widgets are not meant for reuse and will raise this error when reuse is
    attempted.
    """

    def __init__(self, cls: type) -> None:
        super().__init__(f"Instances of {cls} are not allowed to be reused.")

    # https://github.com/sphinx-doc/sphinx/issues/7493
    __module__ = "ssst"


class UnexpectedEmissionError(InternalError):
    """Like an :class:`ssst.InternalError`, but specifically for emissions that we
    didn't expect.
    """

    def __init__(self, emission: "qtrio.Emission") -> None:
        super().__init__(f"Unexpected emission: {emission!r}")

    # https://github.com/sphinx-doc/sphinx/issues/7493
    __module__ = "ssst"
