"""Top-level package for SSST."""

from ssst._version import __version__

from ssst.exceptions import (
    SsstError,
    BaseAddressNotFoundError,
    InternalError,
    InvalidBaseAddressError,
    InvalidActionError,
    ModbusError,
    QtpyError,
    ReuseError,
    UnexpectedEmissionError,
)
