import enum
import os
import pathlib
import subprocess
import sys
import sysconfig
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


def configure_qtpy(api: QtApis) -> None:
    """Set the configuration such that QtPy will use the specified Qt wrapper API.

    Args:
        api: The Qt wrapper API for QtPy to use.
    """
    if "qtpy" in sys.modules:
        raise ssst.exceptions.QtpyError("qtpy imported prior to configuring the API")

    if qt_api_variable_name not in os.environ:
        os.environ[qt_api_variable_name] = api.value


def scripts_path() -> pathlib.Path:
    """Get the path where console and GUI scripts are created.  For example, in Linux
    this may be ``env/bin/`` and on Windows perhaps ``env/scripts/``.  Uses
    :func:`sysconfig.get_path`.

    Returns:
        The scripts directory path.

    Raises:
        ssst.InternalError: if :func:`sysconfig.get_path` returns :obj:`None`.
    """
    maybe_scripts_path_string = sysconfig.get_path("scripts")
    if maybe_scripts_path_string is None:  # pragma: no cover
        raise ssst.InternalError("No scripts path defined.")

    return pathlib.Path(maybe_scripts_path_string)


def script_path(name: str) -> pathlib.Path:
    """Get the path to a console or GUI script of the given name.  This does include
    the ``.exe`` extension on Windows.

    Arguments:
        name: The name of the script to get the path for.

    Returns:
        The path to the script.

    Raises:
        ssst.InternalError: see :func:`ssst._utilities.scripts_path`.
    """

    base_path = scripts_path().joinpath(name)

    if sys.platform == "win32":
        full_path = base_path.with_suffix(".exe")
    else:
        full_path = base_path

    return full_path


def compile_ui(
    directory_path: typing.Sequence[pathlib.Path] = (
        pathlib.Path(ssst.__file__).parent,
    ),
    output: typing.Optional[typing.Callable[..., object]] = None,
) -> None:
    """Compile the specified Qt UI files to Python source that can be imported and
    used.  The files are found by searching the passed directory path for ``*.ui``
    files which are compiled to ``*_ui.py`` within the same directory.

    Arguments:
        directory_path
    """
    generic_compile_ui(
        directory_paths=directory_path,
        output=output,
    )


# TODO: This .ui building bit was 'extracted' from alqtendpy and likely belongs not
#       here.
#       https://github.com/altendky/ssst/issues/15


def generic_compile_ui(
    file_paths: typing.Sequence[pathlib.Path] = (),
    directory_paths: typing.Sequence[pathlib.Path] = (),
    extension: str = ".ui",
    suffix: str = "_ui",
    encoding: str = "utf-8",
    output: typing.Optional[typing.Callable[..., object]] = None,
) -> None:
    """Compile the specified Qt UI files to Python source.  In addition to the passed
    file paths, the passed directory paths are searched to find additional files to
    compile.  The search is done based on the passed extension.  Taking the default
    ``".ui"`` extension and ``"_ui"`` suffix for the sake of an example, an input file
    such as ``x.ui`` will be output as ``x_ui.py`` in the same directory.  The passed
    encoding is used when writing the Python file.

    If not :obj:`None`, the passed output callable will be used like :func:`print` to
    produce any output.

    Arguments:
        file_paths: Paths to individual UI files to be compiled.
        directory_paths: Paths of directories to be searched for UI files to compile.
        extension: The extension used to identify UI files when searching.
        suffix: The suffix to add to the stem of the UI file when creating the Python
            file names.
        encoding: The encoding to use when writing the Python files.
        output: The function to call when there is output that would normally be
            printed.
    """
    paths = [
        *(pathlib.Path(path) for path in file_paths),
        *(
            path
            for directory in directory_paths
            for path in pathlib.Path(directory).rglob("*" + extension)
        ),
    ]

    compile_paths(
        ui_paths=paths,
        suffix=suffix,
        encoding=encoding,
        output=output,
    )


def _do_nothing(*args: object, **kwargs: object) -> None:
    """Accept any arguments and do nothing.  This exists for use as a default for
    :func:`ssst._utilities.compile_ui`."""


def compile_paths(
    ui_paths: typing.Sequence[pathlib.Path],
    suffix: str = "_ui",
    encoding: str = "utf-8",
    output: typing.Optional[typing.Callable[..., object]] = None,
) -> None:
    """Compile the passed UI paths to Python files.  The passed suffix will be added
    to the stem of each file compiled and the extension changed to ``.py`` to create
    the output file name within the same directory.  The passed encoding will be used
    when writing the Python file.

    Arguments:
        ui_paths: The UI files to compile to Python.
        suffix: The suffix to add to the stem when creating the Python file name.
        encoding: The encoding to use when writing the Python file.
        output: The :func:`print`-alike output function to call.  :obj:`None` results
            in no output.

    Raises:
        ssst.QtpyError: If the ``qtpy`` module is not already imported and the import
            has not been forced.
    """
    if output is None:
        output = _do_nothing

    if "qtpy" not in sys.modules:
        raise ssst.QtpyError(
            "QtPy is expected to be imported before calling this function.",
        )

    # If you import at the top you hazard beating the configuration of QtPy.  Not
    # a preferred design but it is reality.
    import qtpy

    for in_path in ui_paths:
        out_path = in_path.with_name(f"{in_path.stem}{suffix}.py")

        output(f"Converting: {in_path} -> {out_path}")

        script_name = {
            "PyQt5": "pyuic5",
            "PySide2": "pyside2-uic",
        }[qtpy.API_NAME]

        completed_process = subprocess.run(
            [os.fspath(script_path(name=script_name)), os.fspath(in_path)],
            check=True,
            stdout=subprocess.PIPE,
        )

        intermediate = completed_process.stdout.decode("utf-8")
        intermediate = intermediate.replace(f"from {qtpy.API_NAME}", "from qtpy")

        out_path.write_text(intermediate, encoding=encoding)
