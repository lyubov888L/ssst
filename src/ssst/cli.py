import click

import ssst._utilities


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option(
    "--qt-api",
    "qt_api_string",
    choices=sorted(ssst._utilities.qt_api_cli_names.keys()),
    default=ssst._utilities.QtApis.default.value,
    help=(
        f"Default uses PySide2 if {ssst._utilities.qt_api_variable_name} is not set."
    ),
)
def gui(qt_api_string: str) -> None:
    qt_api = ssst._utilities.qt_api_cli_names[qt_api_string]
    ssst._utilities.configure_and_import_qtpy(api=qt_api)
