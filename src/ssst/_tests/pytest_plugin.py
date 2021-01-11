import _pytest.config
import _pytest.config.argparsing

import ssst.cli
import ssst._utilities


def pytest_addoption(parser: _pytest.config.argparsing.Parser) -> None:
    group = parser.getgroup("SSST")

    group.addoption(
        "--qt-api",
        choices=sorted(ssst.cli.qt_api_cli_names.keys()),
        default=ssst.cli.automatic_api_cli_name,
        help=(
            f"Default uses PySide2 if {ssst._utilities.qt_api_variable_name} is not"
            f" set."
        ),
    )


def pytest_configure(config: _pytest.config.Config) -> None:
    qt_api_string = config.getoption("--qt-api")
    qt_api = ssst.cli.qt_api_cli_names[qt_api_string]
    ssst._utilities.configure_qtpy(api=qt_api)
