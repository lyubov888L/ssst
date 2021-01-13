import ssst._tests.conftest
import ssst.sunspec


async def test_base_address_marker(
    sunspec_client: ssst.sunspec.client.Client,
):
    register_bytes = await sunspec_client.read_registers(address=40_000, count=2)

    assert register_bytes == ssst.sunspec.base_address_sentinel


async def test_addresses(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
):
    point = sunspec_server.server[17].points["Bits"]
    assert point.model.model_addr + point.offset == 40_078


async def test_write_registers(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
):
    model = sunspec_server.server[1]
    point = model.points["DA"]
    address = model.model_addr + point.offset
    new_id = 43928

    bytes_to_write = point.info.to_data(new_id)
    await sunspec_client.write_registers(address=address, values=bytes_to_write)

    assert point.get_mb() == bytes_to_write
