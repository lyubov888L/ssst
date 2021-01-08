import functools
import typing

import click

import ssst._utilities


automatic_api_cli_name = "automatic"


qt_api_cli_names: typing.Dict[str, typing.Optional[ssst._utilities.QtApis]] = {
    "pyqt5": ssst._utilities.QtApis.PyQt5,
    "pyside2": ssst._utilities.QtApis.PySide2,
    automatic_api_cli_name: None,
}
"""A mapping from the strings used on the CLI to the wrapper API enumerators."""


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option(
    "--qt-api",
    "qt_api_string",
    type=click.Choice(choices=sorted(qt_api_cli_names.keys())),
    default=automatic_api_cli_name,
    help=(
        f"Default lets QtPy choose.  {ssst._utilities.qt_api_variable_name} will be"
        f" used if set."
    ),
)
def gui(qt_api_string: str) -> None:  # pragma: no cover
    # TODO: This is generally actually covered by
    #       ssst._tests.test_cli.test_gui_persists but the coverage recording or
    #       reporting isn't working out.
    #       https://github.com/altendky/ssst/issues/13

    import ssst._utilities

    qt_api = qt_api_cli_names[qt_api_string]

    if qt_api is not None:
        ssst._utilities.configure_qtpy(api=qt_api)

    import ssst.gui.main
    import qtrio

    qtrio.run(functools.partial(ssst.gui.main.Window.start, title="SSST"))


@cli.command()
def uic() -> None:  # pragma: no cover
    # Coverage not required during testing since this has to work to create all the
    # UI modules that the tests exercise anyways.  Sort of...
    import ssst._utilities

    ssst._utilities.compile_ui(output=click.echo)
