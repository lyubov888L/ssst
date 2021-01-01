import click.testing
import pytest

import ssst.cli


commands = [ssst.cli.cli, ssst.cli.gui]


@pytest.mark.parametrize(
    argnames=["command"],
    argvalues=[[command] for command in commands],
    ids=[command.name for command in commands],
)
def test_help_does_not_fail(
    command: click.Command, cli_runner: click.testing.CliRunner
) -> None:
    result = cli_runner.invoke(command, args=["--help"])
    assert result.exit_code == 0
