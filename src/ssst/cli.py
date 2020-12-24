import typing

import click

import ssst._utilities


qt_api_cli_names: typing.Dict[str, typing.Optional[ssst._utilities.QtApis]] = {
    "pyqt5": ssst._utilities.QtApis.PyQt5,
    "pyside2": ssst._utilities.QtApis.PySide2,
    "automatic": None,
}
"""A mapping from the strings used on the CLI to the wrapper API enumerators."""


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option(
    "--qt-api",
    "qt_api_string",
    choices=sorted(qt_api_cli_names.keys()),
    default=None,
    help=(
        f"Default uses PySide2 if {ssst._utilities.qt_api_variable_name} is not set."
    ),
)
def gui(qt_api_string: str) -> None:
    qt_api = qt_api_cli_names[qt_api_string]
    ssst._utilities.configure_qtpy(api=qt_api)
