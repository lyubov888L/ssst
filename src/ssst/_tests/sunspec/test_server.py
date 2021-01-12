import functools

import attr
import pymodbus.client.asynchronous.tcp
import pymodbus.client.asynchronous.schedulers
import pytest
import trio

import ssst.sunspec.server


@attr.s(auto_attribs=True, frozen=True)
class SunSpecServerFixtureResult:
    host: str
    port: int


@pytest.fixture(name="sunspec_server")
async def sunspec_server_fixture(nursery):
    model_summaries = [
        ssst.sunspec.server.ModelSummary(id=1, length=66),
    ]

    server_callable = ssst.sunspec.server.create_server_callable(
        model_summaries=model_summaries
    )

    result = SunSpecServerFixtureResult(host="127.0.0.1", port=5020)

    await nursery.start(
        functools.partial(
            trio.serve_tcp,
            server_callable,
            port=result.port,
            host=result.host,
        ),
    )

    yield result


@pytest.fixture(name="sunspec_client")
async def sunspec_client_fixture(sunspec_server):
    client = pymodbus.client.asynchronous.tcp.AsyncModbusTCPClient(
        scheduler=pymodbus.client.asynchronous.schedulers.TRIO,
        host=sunspec_server.host,
        port=sunspec_server.port,
    )

    async with client.manage_connection() as protocol:
        yield protocol


async def test_server_SunS(sunspec_client):
    response = await sunspec_client.read_holding_registers(
        address=40_000, count=2, unit=0x01
    )

    assert bytes(response.registers) == b"SunS"


async def test_server_set_device_address(sunspec_client):
    register = 40_068
    length = 1
    new_id = 43928
    b = new_id.to_bytes(length=2 * length, byteorder="big")

    await sunspec_client.write_registers(
        address=register, values=b, unit=0x01
    )

    response = await sunspec_client.read_holding_registers(
        address=register, count=length, unit=0x01
    )

    assert int.from_bytes(bytes(response.registers), byteorder="big") == new_id
