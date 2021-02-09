import os
import pathlib
import sys
import typing

import click.testing
import importlib_metadata
import pytest

# TODO: Shouldn't be importing private stuff.
#       https://github.com/pytest-dev/pytest/issues/8073
import _pytest.fixtures
import trio

import ssst.cli
import ssst._utilities

ClickItem = typing.Union[click.Group, click.Command]


def all_flat(items: typing.Sequence[ClickItem]) -> typing.List[ClickItem]:
    all_items = []
    all_items_set = set()
    to_visit = list(items)

    while len(to_visit) > 0:
        item = to_visit.pop(0)
        # No branch coverage required for this test helper presently
        if item not in all_items_set:  # pragma: no branch
            all_items_set.add(item)
            all_items.append(item)
        subitems = getattr(item, "commands", None)

        if subitems is not None:
            to_visit.extend(subitems.values())

    return all_items


items = all_flat(items=[ssst.cli.cli])


@pytest.mark.parametrize(
    argnames=["item"],
    argvalues=[[item] for item in items],
    ids=[item.name for item in items],
)
def test_help_does_not_fail(
    item: click.Command, cli_runner: click.testing.CliRunner
) -> None:
    result = cli_runner.invoke(item, args=["--help"])
    assert result.exit_code == 0


def test_one_matching_entry_point_provided() -> None:
    # TODO: This really belongs elsewhere as it is testing setup.cfg.
    # TODO: hint rather than...  Any'ing I guess?
    all_entry_points = importlib_metadata.entry_points()  # type: ignore[no-untyped-call]
    all_console_scripts = all_entry_points["console_scripts"]
    our_console_scripts = [
        script for script in all_console_scripts if script.value.startswith("ssst.")
    ]

    # TODO: pytest seems to make a duplicate entry compared to checking with
    #  'just Python'.  No idea why right now, just accepting it.
    our_consolidated_console_scripts = []
    for script in our_console_scripts:
        if script not in our_consolidated_console_scripts:
            our_consolidated_console_scripts.append(script)

    assert len(our_consolidated_console_scripts) == 1, our_consolidated_console_scripts


@pytest.fixture(name="launch_command", params=["script", "-m", "frozen"])
def launch_command_fixture(
    request: _pytest.fixtures.SubRequest,
    frozen_executable: typing.Optional[pathlib.Path],
) -> typing.List[str]:
    """This launch command fixture will return a list of strings that can be used as
    a subprocess command to launch the base SSST program.  There are three possible
    modes.
    
    - myvenv/bin/ssst
    - myvenv/bin/python -m ssst
    - dist/myfrozenssst
    
    If --frozen-executable has been specified then the first two will be skipped.
    Otherwise, the frozen executable mode will be skipped.
    """
    
    if request.param == "script":
        if frozen_executable is not None:
            pytest.skip("Frozen executable specified, skipping non-frozen tests")

        ssst_path = ssst._utilities.script_path(name="ssst")

        return [os.fspath(ssst_path)]
    elif request.param == "-m":
        if frozen_executable is not None:
            pytest.skip("Frozen executable specified, skipping non-frozen tests")

        return [sys.executable, "-m", "ssst"]
    elif request.param == "frozen":
        if frozen_executable is None:
            pytest.skip("Frozen executable not specified, pass via --frozen-executable")

        return [os.fspath(frozen_executable)]

    raise ssst.InternalError("Unhandled parametrization")  # pragma: no cover


async def test_gui_launches(
    nursery: trio.Nursery, tmp_path: pathlib.Path, launch_command: typing.List[str]
) -> None:
    # TODO: this should be written to use logging features to see where the GUI has
    # traversed to.

    debug_path = tmp_path.joinpath("debug_file")
    debug_bytes = b"lkjflkjnlknrlfaljfdsaoivjxcewa\n981439874298785379876298349887\n"

    async def run() -> None:
        # Remember that many exceptions will be caught sufficiently to present in
        # a dialog which will keep the process running indefinitely.

        await trio.run_process(
            [*launch_command, "gui"],
            env={
                **os.environ,
                "SSST_DEBUG_FILE": os.fspath(debug_path),
                "SSST_DEBUG_BYTES": debug_bytes.decode("ASCII"),
            },
        )

    nursery.start_soon(run)

    with trio.fail_after(seconds=40):
        while True:
            await trio.sleep(0.2)

            if debug_path.exists():
                break

    assert debug_path.read_bytes() == debug_bytes
