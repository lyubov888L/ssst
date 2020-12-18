import _pytest.config
import _pytest.config.argparsing

import ssst._utilities


def pytest_addoption(parser: _pytest.config.argparsing.Parser) -> None:
    group = parser.getgroup("grid-tied")

    group.addoption(
        "--qt-api",
        choices=sorted(ssst._utilities.qt_api_cli_names.keys()),
        default=ssst._utilities.QtApis.default.value,
        help=(
            f"Default uses PySide2 if {ssst._utilities.qt_api_variable_name} is not"
            f" set."
        ),
    )


def pytest_configure(config: _pytest.config.Config) -> None:
    qt_api_string = config.getoption("--qt-api")
    qt_api = ssst._utilities.qt_api_cli_names[qt_api_string]
    ssst._utilities.configure_and_import_qtpy(api=qt_api)
