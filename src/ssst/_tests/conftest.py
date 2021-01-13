import functools
import typing

import attr
import click.testing
import pymodbus.client.asynchronous.tcp
import pymodbus.client.asynchronous.schedulers
import pytest
import trio

import ssst.sunspec.client
import ssst.sunspec.server


pytest_plugins = "pytester"


# TODO: consider pytest-click


@pytest.fixture(name="cli_runner")
def cli_runner_fixture() -> typing.Iterator[click.testing.CliRunner]:
    cli_runner = click.testing.CliRunner()
    with cli_runner.isolated_filesystem():
        yield cli_runner


@attr.s(auto_attribs=True, frozen=True)
class SunSpecServerFixtureResult:
    host: str
    port: int
    server: ssst.sunspec.server.Server


@pytest.fixture(name="sunspec_server")
async def sunspec_server_fixture(nursery):
    model_summaries = [
        ssst.sunspec.server.ModelSummary(id=1, length=66),
        ssst.sunspec.server.ModelSummary(id=17, length=12),
        ssst.sunspec.server.ModelSummary(id=103, length=50),
        ssst.sunspec.server.ModelSummary(id=126, length=226),
    ]

    server = ssst.sunspec.server.Server.build(model_summaries=model_summaries)

    host = "127.0.0.1"

    [listener] = await nursery.start(
        functools.partial(
            trio.serve_tcp,
            server.tcp_server,
            host=host,
            port=0,
        ),
    )

    yield SunSpecServerFixtureResult(
        host=host,
        port=listener.socket.getsockname()[1],
        server=server,
    )


@pytest.fixture(name="unscanned_sunspec_client")
async def unscanned_sunspec_client_fixture(sunspec_server):
    client = ssst.sunspec.client.Client.build(
        host=sunspec_server.host,
        port=sunspec_server.port,
    )

    async with client.manage_connection():
        yield client


@pytest.fixture(name="sunspec_client")
async def sunspec_client_fixture(unscanned_sunspec_client):
    await unscanned_sunspec_client.scan()
    return unscanned_sunspec_client
