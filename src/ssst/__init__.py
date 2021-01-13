"""Top-level package for SSST."""

from ssst._version import __version__

from ssst.exceptions import (
    BaseAddressNotFoundError,
    InternalError,
    InvalidBaseAddressError,
    QtpyError,
    ReuseError,
    SsstError,
    UnexpectedEmissionError,
)
