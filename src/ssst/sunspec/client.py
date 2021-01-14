import typing

import async_generator
import attr
import pymodbus.client.asynchronous.schedulers
import pymodbus.client.asynchronous.tcp
import pymodbus.client.asynchronous.trio
import pymodbus.client.common
import sunspec2.mb
import sunspec2.modbus.client
import pymodbus.pdu

import ssst.sunspec


@async_generator.asynccontextmanager
async def open_client(host: str, port: int) -> typing.AsyncIterator["Client"]:
    """Open a SunSpec Modbus TCP connection to the passed host and port.

    Arguments:
        host: The host name or IP address.
        port: The port number.

    Yields:
        The SunSpec client.
    """

    modbus_client = pymodbus.client.asynchronous.tcp.AsyncModbusTCPClient(
        scheduler=pymodbus.client.asynchronous.schedulers.TRIO,
        host=host,
        port=port,
    )
    sunspec_device = sunspec2.modbus.client.SunSpecModbusClientDevice()

    async with modbus_client.manage_connection() as protocol:
        yield Client(
            modbus_client=modbus_client,
            sunspec_device=sunspec_device,
            protocol=protocol,
        )


@attr.s(auto_attribs=True)
class Client:
    """A SunSpec Modbus TCP client using :mod:`trio` support in :mod:`pymodbus` for
    communication and `pysunspec2` for loading models and holding the local cache of
    the data.  The existing communication abilities of the `pysunspec2` objects are
    left intact but should not be used.

    .. automethod:: __getitem__
    """

    modbus_client: pymodbus.client.asynchronous.trio.TrioModbusTcpClient
    """The Modbus TCP client used for communication."""
    protocol: pymodbus.client.common.ModbusClientMixin
    """The Modbus client protocol."""
    sunspec_device: sunspec2.modbus.client.SunSpecModbusClientDevice
    """The SunSpec device object that holds the local data cache and model structures.
    """

    def __getitem__(
        self, item: typing.Union[int, str]
    ) -> sunspec2.modbus.client.SunSpecModbusClientModel:
        """SunSpec models are accessible by indexing the client using either the model
        number or model name.

        .. code-block:: python

            model_1 = client[1]
            model_common = client["common"]
            assert model_1 is model_common

        Returns:
            The requested model.
        """
        [model] = self.sunspec_device.models[item]
        return model

    async def scan(self) -> None:
        """Scan the device to identify the base address, if not already set, and
        collect the model list.  This also populates all the data.
        """
        if self.sunspec_device.base_addr is None:
            for maybe_base_address in self.sunspec_device.base_addr_list:
                read_bytes = await self.read_registers(
                    address=maybe_base_address,
                    count=len(ssst.sunspec.base_address_sentinel) // 2,
                )
                if read_bytes == ssst.sunspec.base_address_sentinel:
                    self.sunspec_device.base_addr = maybe_base_address
                    break
            else:
                raise ssst.BaseAddressNotFoundError(
                    addresses=self.sunspec_device.base_addr_list
                )
        else:
            read_bytes = await self.read_registers(
                address=self.sunspec_device.base_addr,
                count=len(ssst.sunspec.base_address_sentinel) // 2,
            )
            if read_bytes != ssst.sunspec.base_address_sentinel:
                raise ssst.InvalidBaseAddressError(
                    address=self.sunspec_device.base_addr,
                    value=read_bytes,
                )

        address = (
            self.sunspec_device.base_addr + len(ssst.sunspec.base_address_sentinel) // 2
        )
        model_id_length = 1
        model_length_length = 1

        while True:
            model_address = address
            intra_model_address = address
            read_bytes = await self.read_registers(
                address=address, count=model_id_length
            )
            intra_model_address += model_id_length
            maybe_model_id = int.from_bytes(
                bytes=read_bytes, byteorder="big", signed=False
            )
            if maybe_model_id == sunspec2.mb.SUNS_END_MODEL_ID:
                break

            model_id = maybe_model_id

            read_bytes = await self.read_registers(
                address=intra_model_address, count=model_length_length
            )
            intra_model_address += model_length_length
            model_length = int.from_bytes(
                bytes=read_bytes, byteorder="big", signed=False
            )

            # TODO: oof, awkward way to write this it seems
            whole_model_length = (intra_model_address - address) + model_length
            model_data = self.read_registers(address=address, count=whole_model_length)
            address += whole_model_length

            model = sunspec2.modbus.client.SunSpecModbusClientModel(
                model_id=model_id,
                model_addr=model_address,
                model_len=model_length,
                data=model_data,
                mb_device=self.sunspec_device,
            )
            self.sunspec_device.add_model(model)

    # TODO: should the local data be updated?
    async def read_registers(self, address: int, count: int) -> bytes:
        """Read from the specified sequential register range in the device.  Based on
        the 16-bit Modbus register size, the data in the returned bytes is in 2-byte
        chunks with each having a big-endian byte order.  The local data is not
        updated.

        Arguments:
            address: The first register to read.
            count: The total number of sequential registers to read.

        Returns:
            The raw bytes read from the device.

        Raises:
            ssst.ModbusError: When a Modbus exception response is received.
        """

        response = await self.protocol.read_holding_registers(
            address=address, count=count, unit=0x01
        )

        if isinstance(response, pymodbus.pdu.ExceptionResponse):
            raise ssst.ModbusError(exception=response)

        return bytes(response.registers)

    async def read_point(
        self, point: sunspec2.modbus.client.SunSpecModbusClientPoint
    ) -> typing.Union[float, int]:
        """Read the passed point from the device and update the local data.

        Arguments:
            point: The SunSpec point object to read.

        Returns:
            The new computed value of the point.

        Raises:
            ssst.ModbusError: When a Modbus exception response is received.
        """
        if point.sf is not None:
            await self.read_point(point=point.model.points[point.sf])

        read_bytes = await self.read_registers(
            address=self.point_address(point=point),
            count=point.len,
        )
        point.set_mb(data=read_bytes)

        if point.pdef["type"] == "sunssf":
            for other_point in point.model.points.values():
                if other_point.sf == point.pdef["name"]:
                    other_cvalue = other_point.cvalue
                    other_point.sf_value = point.cvalue
                    if other_cvalue is not None:
                        other_point.cvalue = other_cvalue

        return point.cvalue  # type: ignore[no-any-return]

    def point_address(
        self, point: sunspec2.modbus.client.SunSpecModbusClientPoint
    ) -> int:
        """Calculate the start address of a given SunSpec point.

        Arguments:
            point: The SunSpec point object to read.

        Returns:
            The address of the first register of the point.
        """
        return point.model.model_addr + point.offset  # type: ignore[no-any-return]

    async def write_registers(self, address: int, values: bytes) -> None:
        """Write to the specified sequential register range in the device.  Based on
        the 16-bit Modbus register size, the data in the passed bytes should in 2-byte
        chunks with each having a big-endian byte order.  The local data is not
        updated.

        Arguments:
            address: The first register to write.
            count: The total number of sequential registers to write.

        Returns:
            The raw bytes to be written to the device.

        Raises:
            ssst.ModbusError: When a Modbus exception response is received.
        """
        response = await self.protocol.write_registers(
            address=address, values=values, unit=0x01
        )

        if isinstance(response, pymodbus.pdu.ExceptionResponse):
            raise ssst.ModbusError(exception=response)

    async def write_point(
        self, point: sunspec2.modbus.client.SunSpecModbusClientPoint
    ) -> None:
        """Write the passed point from the local data to the device.

        Arguments:
            point: The SunSpec point object to write.

        Raises:
            ssst.ModbusError: When a Modbus exception response is received.
        """
        if point.sf is not None:
            await self.read_point(point=point.model.points[point.sf])

        bytes_to_write = point.get_mb()
        await self.write_registers(
            address=self.point_address(point=point),
            values=bytes_to_write,
        )
