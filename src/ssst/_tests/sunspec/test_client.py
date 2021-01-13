import ssst._tests.conftest
import ssst.sunspec.client
import ssst.sunspec.server


async def test_scan_adds_models(sunspec_client: ssst.sunspec.client.Client):
    model_ids = [model.model_id for model in sunspec_client.sunspec_device.model_list]

    assert model_ids == [1, 17, 103, 126]


async def test_model_addresses(sunspec_client: ssst.sunspec.client.Client):
    model_ids = [model.model_addr for model in sunspec_client.sunspec_device.model_list]

    assert model_ids == [40_002, 40_070, 40_084, 40_136]


async def test_point_address(
    sunspec_client: ssst.sunspec.client.Client,
):
    point = sunspec_client[17].points["Bits"]
    assert point.model.model_addr + point.offset == 40_078


async def test_read_point_by_registers(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
):
    model = sunspec_server.server[1]
    point = model.points["DA"]
    address = model.model_addr + point.offset
    length = 1
    new_id = 43928

    written_bytes = point.info.to_data(new_id)
    point.set_mb(written_bytes)

    read_bytes = await sunspec_client.read_registers(address=address, count=length)

    assert read_bytes == written_bytes
    assert int.from_bytes(read_bytes, byteorder="big") == new_id


async def test_read_point_with_scale_factor(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
):
    server_point = sunspec_server.server[103].points["W"]
    server_scale_factor_point = server_point.model.points[server_point.sf]

    scale_factor = 2
    scaled_watts = 473

    server_scale_factor_point.set_mb(
        data=server_scale_factor_point.info.to_data(scale_factor),
    )
    server_point.set_mb(
        data=server_point.info.to_data(scaled_watts),
    )

    point = sunspec_client[103].points["W"]
    scale_factor_point = point.model.points[point.sf]

    read_scale_factor = await sunspec_client.read_point(point=scale_factor_point)
    assert read_scale_factor == scale_factor

    read_value = await sunspec_client.read_point(point=point)
    assert read_value == scaled_watts
