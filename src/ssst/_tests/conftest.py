import functools
import pathlib
import typing

import attr
import click.testing
import pymodbus.client.asynchronous.tcp
import pymodbus.client.asynchronous.schedulers
import pytest
import _pytest.fixtures
import trio

import ssst.sunspec.client
import ssst.sunspec.server


pytest_plugins = "pytester"


# TODO: consider pytest-click


@pytest.fixture(name="frozen_executable", scope="session")
def frozen_executable_fixture(
    request: _pytest.fixtures.SubRequest,
) -> typing.Optional[pathlib.Path]:
    maybe_frozen_executable_string = request.config.getoption("--frozen-executable")

    if maybe_frozen_executable_string is None:
        return None

    return pathlib.Path(maybe_frozen_executable_string)


@pytest.fixture(name="_maybe_skip_not_frozen", autouse=True, scope="function")
def _maybe_skip_not_frozen_fixture(request: _pytest.fixtures.SubRequest):
    frozen_executable_specified = (
        request.config.getoption("--frozen-executable") is not None
    )
    uses_frozen_executable = "frozen_executable" in request.fixturenames

    if frozen_executable_specified and not uses_frozen_executable:
        pytest.skip("Frozen executable specified, skipping non-frozen tests")


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
async def sunspec_server_fixture(
    nursery: trio.Nursery,
) -> typing.AsyncIterator[SunSpecServerFixtureResult]:
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
async def unscanned_sunspec_client_fixture(
    sunspec_server: SunSpecServerFixtureResult,
) -> typing.AsyncIterator[ssst.sunspec.client.Client]:
    async with ssst.sunspec.client.open_client(
        host=sunspec_server.host,
        port=sunspec_server.port,
    ) as client:
        yield client


@pytest.fixture(name="sunspec_client")
async def sunspec_client_fixture(
    unscanned_sunspec_client: ssst.sunspec.client.Client,
) -> ssst.sunspec.client.Client:
    await unscanned_sunspec_client.scan()
    return unscanned_sunspec_client
