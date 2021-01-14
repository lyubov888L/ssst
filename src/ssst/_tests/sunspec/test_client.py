import re

import pytest

import ssst._tests.conftest
import ssst.sunspec.client
import ssst.sunspec.server


async def test_scan_adds_models(sunspec_client: ssst.sunspec.client.Client) -> None:
    model_ids = [model.model_id for model in sunspec_client.sunspec_device.model_list]

    assert model_ids == [1, 17, 103, 126]


async def test_scan_raises_for_missing_sentinel_when_searching(
    unscanned_sunspec_client: ssst.sunspec.client.Client,
) -> None:
    unscanned_sunspec_client.sunspec_device.base_addr_list[:] = [40_010, 40_020]

    message = "SunSpec sentinel b'SunS' not found while searching: 40010, 40020"
    with pytest.raises(ssst.BaseAddressNotFoundError, match=f"^{re.escape(message)}$"):
        await unscanned_sunspec_client.scan()


async def test_scan_raises_for_missing_sentinel_when_address_specified(
    unscanned_sunspec_client: ssst.sunspec.client.Client,
) -> None:
    unscanned_sunspec_client.sunspec_device.base_addr = 40_001

    message = r"SunSpec sentinel b'SunS' not found at 40001: b'nS\x00\x01'"
    with pytest.raises(ssst.InvalidBaseAddressError, match=f"^{re.escape(message)}$"):
        await unscanned_sunspec_client.scan()


async def test_model_addresses(sunspec_client: ssst.sunspec.client.Client) -> None:
    model_ids = [model.model_addr for model in sunspec_client.sunspec_device.model_list]

    assert model_ids == [40_002, 40_070, 40_084, 40_136]


async def test_point_address(
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    point = sunspec_client[17].points["Bits"]
    assert point.model.model_addr + point.offset == 40_078


async def test_read_point_by_registers(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
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


async def test_read_point(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    new_id = 43928

    server_point = sunspec_server.server[1].points["DA"]
    server_point.cvalue = new_id

    client_point = sunspec_client[1].points["DA"]

    await sunspec_client.read_point(point=client_point)

    assert client_point.cvalue == new_id


async def test_read_point_with_scale_factor(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    server_point = sunspec_server.server[103].points["W"]
    server_scale_factor_point = server_point.model.points[server_point.sf]

    scale_factor = -2
    scaled_watts = 273

    server_scale_factor_point.cvalue = scale_factor
    server_point.cvalue = scaled_watts

    point = sunspec_client[103].points["W"]
    scale_factor_point = point.model.points[point.sf]

    read_scale_factor = await sunspec_client.read_point(point=scale_factor_point)
    assert read_scale_factor == scale_factor

    read_value = await sunspec_client.read_point(point=point)
    assert read_value == scaled_watts


async def test_write_point_by_registers(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    new_id = 43928

    client_point = sunspec_client[1].points["DA"]
    client_point.cvalue = new_id

    await sunspec_client.write_registers(
        address=sunspec_client.point_address(point=client_point),
        values=client_point.get_mb(),
    )

    server_point = sunspec_server.server[1].points["DA"]
    assert server_point.cvalue == new_id


async def test_write_point(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    new_id = 43928

    client_point = sunspec_client[1].points["DA"]
    client_point.cvalue = new_id

    await sunspec_client.write_point(point=client_point)

    server_point = sunspec_server.server[1].points["DA"]
    assert server_point.cvalue == new_id


async def test_write_point_with_scale_factor(
    sunspec_server: ssst._tests.conftest.SunSpecServerFixtureResult,
    sunspec_client: ssst.sunspec.client.Client,
) -> None:
    point = sunspec_client[103].points["W"]
    scale_factor_point = point.model.points[point.sf]

    scale_factor = -2
    scaled_watts = 273

    server_point = sunspec_server.server[103].points["W"]
    server_scale_factor_point = server_point.model.points[server_point.sf]

    server_scale_factor_point.cvalue = scale_factor
    server_point.cvalue = 0

    scale_factor_point.cvalue = 0
    point.cvalue = scaled_watts

    await sunspec_client.write_point(point=point)

    assert point.cvalue == server_point.cvalue == scaled_watts
    assert scale_factor_point.cvalue == server_scale_factor_point.cvalue == scale_factor

    # assert scale_factor_point.cvalue == server_scale_factor_point.cvalue
    # assert server_scale_factor_point.cvalue == scale_factor
    # assert server_point.cvalue == scaled_watts


async def test_read_modbus_exception_raises(
    sunspec_client: ssst.sunspec.client.Client,
):
    with pytest.raises(ssst.ModbusError):
        await sunspec_client.read_registers(address=0, count=1)


async def test_write_modbus_exception_raises(
    sunspec_client: ssst.sunspec.client.Client,
):
    with pytest.raises(ssst.ModbusError):
        await sunspec_client.write_registers(address=0, values=b":]")
