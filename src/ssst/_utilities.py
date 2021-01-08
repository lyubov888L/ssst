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
    generic_compile_ui(
        directory_paths=directory_path,
        output=output,
        rewrite_for_qtpy=True,
    )


# TODO: This .ui building bit was 'extracted' from alqtendpy and likely belongs not
#       here.
#       https://github.com/altendky/ssst/issues/15


def _do_nothing(*args, **kwargs):
    pass


def generic_compile_ui(
    file_paths=(),
    directory_paths=(),
    extension=".ui",
    suffix="_ui",
    encoding="utf-8",
    output=_do_nothing,
    rewrite_for_qtpy=False,
):
    paths = collect_paths(
        file_paths=file_paths,
        directory_paths=directory_paths,
        extension=extension,
    )

    compile_paths(
        ui_paths=paths,
        suffix=suffix,
        encoding=encoding,
        output=output,
        rewrite_for_qtpy=rewrite_for_qtpy,
    )


def collect_paths(file_paths=(), directory_paths=(), extension=".ui"):
    file_paths = [pathlib.Path(path) for path in file_paths]

    for directory in directory_paths:
        path = pathlib.Path(directory)
        found_paths = path.rglob("*" + extension)
        file_paths.extend(found_paths)

    return file_paths


def scripts_path() -> pathlib.Path:
    maybe_scripts_path_string = sysconfig.get_path("scripts")
    if maybe_scripts_path_string is None:
        raise ssst.SsstError()

    return pathlib.Path(maybe_scripts_path_string)


def script_path(name: str) -> pathlib.Path:
    return scripts_path().joinpath(name)


def compile_paths(
    ui_paths,
    suffix="_ui",
    encoding="utf-8",
    output=_do_nothing,
    rewrite_for_qtpy=False,
):
    # If you import at the top you hazard beating the configuration of QtPy.  Not
    # a preferred design but it is reality.

    import qtpy

    for path in ui_paths:
        in_path = path
        out_path = path.with_name(f"{path.stem}{suffix}.py")

        output(f"Converting: {in_path} -> {out_path}")

        script_name = {
            "PyQt5": "pyuic5",
            "PySide2": "pyside2-uic",
        }[qtpy.API_NAME]

        completed_process = subprocess.run(
            [script_path(name=script_name), in_path],
            check=True,
            stdout=subprocess.PIPE,
        )

        intermediate = completed_process.stdout.decode("utf-8")

        if rewrite_for_qtpy:
            intermediate = intermediate.replace(f"from {qtpy.API_NAME}", "from qtpy")

        with open(out_path, "w", encoding=encoding) as out_file:
            out_file.write(intermediate)
