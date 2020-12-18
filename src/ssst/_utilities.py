import enum
import os
import sys

import ssst.exceptions


# must match qtpy.QT_API but we can't import it until we've set this
qt_api_variable_name = "QT_API"


class QtApis(enum.Enum):
    """Supported Qt APIs.  Values correspond to qtpy names for each."""

    PyQt5 = "pyqt5"
    PySide2 = "pyside2"
    default = "default"


default = QtApis.PySide2


qt_api_cli_names = {
    "pyqt5": QtApis.PyQt5,
    "pyside2": QtApis.PySide2,
    "default": QtApis.default,
}


def configure_and_import_qtpy(api: QtApis) -> None:
    if "qtpy" in sys.modules:
        raise ssst.exceptions.QtpyError("qtpy imported prior to selecting which API")

    if qt_api_variable_name not in os.environ:
        if api == QtApis.default:
            api = default

        os.environ[qt_api_variable_name] = api.value

    # Force this present configuration to be used for loading qtpy.  Presumably you
    # will only call this function when you want qtpy loaded so hopefully this doesn't
    # cause pointless importing.  A present quick test takes roughly 30ms to import so
    # this shouldn't contribute unduly to startup latency.

    import qtpy
