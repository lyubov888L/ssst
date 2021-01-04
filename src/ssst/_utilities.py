import enum
import os
import pathlib
import sys
import typing

import ssst
import ssst.exceptions


# must match qtpy.QT_API but we can't import it until we've set this
qt_api_variable_name = "QT_API"
"""The name of the environment variable QtPy checks for selecting the desired
Qt wrapper API."""


class QtApis(enum.Enum):
    """Supported Qt APIs.  Values correspond to qtpy names for each.  Generally used
    as a parameter to :func:`ssst._utilities.configure_qtpy()`.
    """

    PyQt5 = "pyqt5"
    """PyQt5 by Riverbank Computing"""

    PySide2 = "pyside2"
    """PySide2 by Qt"""


def configure_qtpy(api: typing.Optional[QtApis]) -> None:
    """
    Set the configuration such that QtPy will use the specified Qt wrapper API.

    Args:
        api: The Qt wrapper API for QtPy to use.
    """
    if "qtpy" in sys.modules:
        raise ssst.exceptions.QtpyError("qtpy imported prior to configuring the API")

    if qt_api_variable_name not in os.environ:
        if api is not None:
            os.environ[qt_api_variable_name] = api.value


def _no_output(*args: object, **kwargs: object) -> None:
    pass


def compile_ui(
    directory_path: typing.Sequence[pathlib.Path] = (
        pathlib.Path(ssst.__file__).parent,
    ),
    output: typing.Callable[..., object] = _no_output,
) -> None:
    import alqtendpy.compileui

    alqtendpy.compileui.compile_ui(
        directory_paths=directory_path,
        output=output,
        qtpy=True,
    )
