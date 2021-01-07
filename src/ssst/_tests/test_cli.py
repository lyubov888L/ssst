import importlib.metadata
import os
import pathlib
import sysconfig
import typing

import click.testing
import pytest
import trio

import ssst.cli


ClickItem = typing.Union[click.Group, click.Command]


def all_flat(items: typing.Sequence[ClickItem]) -> typing.List[ClickItem]:
    all_items = []
    all_items_set = set()
    to_visit = list(items)

    while len(to_visit) > 0:
        item = to_visit.pop(0)
        if item not in all_items_set:
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


def test_one_matching_entry_point_provided():
    # TODO: This really belongs elsewhere as it is testing setup.cfg.
    all_entry_points = importlib.metadata.entry_points()
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


async def test_gui_persists(nursery, tmp_path):
    # TODO: this should be written to use logging features to see where the GUI has
    # traversed to.

    scripts_path = pathlib.Path(sysconfig.get_path("scripts"))
    ssst_path = scripts_path.joinpath("ssst")

    debug_path = tmp_path.joinpath("debug_file")
    debug_bytes = b"lkjflkjnlknrlfaljfdsaoivjxcewa\n981439874298785379876298349887\n"

    async def run():
        # Remember that many exceptions will be caught sufficiently to present in
        # a dialog which will keep the process running indefinitely.
        await trio.run_process(
            [ssst_path, "gui"],
            env={
                **os.environ,
                "SSST_DEBUG_FILE": os.fspath(debug_path),
                "SSST_DEBUG_BYTES": debug_bytes,
            },
        )

    nursery.start_soon(run)

    with trio.fail_after(seconds=40):
        while True:
            await trio.sleep(0.2)

            if debug_path.exists():
                break

    assert debug_path.read_bytes() == debug_bytes
