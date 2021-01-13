import ssst._tests.conftest
import ssst.sunspec
import ssst.sunspec.client


async def test_base_address_marker(
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    register_bytes = await sunspec_client.read_registers(address=40_000, count=2)

    assert register_bytes == ssst.sunspec.base_address_sentinel


async def test_addresses(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
) -> None:
    point = sunspec_server.server[17].points["Bits"]
    assert point.model.model_addr + point.offset == 40_078


async def test_write_registers(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    model = sunspec_server.server[1]
    point = model.points["DA"]
    address = model.model_addr + point.offset
    new_id = 43928

    bytes_to_write = point.info.to_data(new_id)
    await sunspec_client.write_registers(address=address, values=bytes_to_write)

    assert point.get_mb() == bytes_to_write


async def test_read_bus_value_scaled_as_expected(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    server_point = sunspec_server.server[103].points["W"]
    server_scale_factor_point = server_point.model.points[server_point.sf]

    scale_factor = -2
    scaled_watts = 47.35

    server_scale_factor_point.cvalue = scale_factor
    server_point.cvalue = scaled_watts

    client_point = sunspec_client[103].points["W"]

    await sunspec_client.read_point(point=client_point)
    assert client_point.value == scaled_watts / 10 ** scale_factor
