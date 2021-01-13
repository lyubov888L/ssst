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


@attr.s(auto_attribs=True)
class Client:
    modbus_client: pymodbus.client.asynchronous.trio.TrioModbusTcpClient
    sunspec_device: sunspec2.modbus.client.SunSpecModbusClientDevice
    protocol: typing.Optional[pymodbus.client.common.ModbusClientMixin] = None

    @classmethod
    def build(cls, host: str, port: int) -> "Client":
        modbus_client = pymodbus.client.asynchronous.tcp.AsyncModbusTCPClient(
            scheduler=pymodbus.client.asynchronous.schedulers.TRIO,
            host=host,
            port=port,
        )
        sunspec_device = sunspec2.modbus.client.SunSpecModbusClientDevice()

        return cls(modbus_client=modbus_client, sunspec_device=sunspec_device)

    @async_generator.asynccontextmanager
    async def manage_connection(self) -> typing.AsyncIterator["Client"]:
        try:
            async with self.modbus_client.manage_connection() as self.protocol:
                yield self
        finally:
            self.protocol = None

    def __getitem__(
        self, item: typing.Union[int, str]
    ) -> sunspec2.modbus.client.SunSpecModbusClientModel:
        [model] = self.sunspec_device.models[item]
        return model

    async def scan(self) -> None:
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

    async def read_registers(self, address: int, count: int) -> bytes:
        if self.protocol is None:
            raise ssst.InvalidActionError("Cannot read without a managed connection.")

        response = await self.protocol.read_holding_registers(
            address=address, count=count, unit=0x01
        )

        if isinstance(response, pymodbus.pdu.ExceptionResponse):
            raise ssst.ModbusError(exception=response)

        return bytes(response.registers)

    async def read_point(
        self, point: sunspec2.modbus.client.SunSpecModbusClientPoint
    ) -> typing.Union[float, int]:
        if point.sf is not None:
            await self.read_point(point=point.model.points[point.sf])

        read_bytes = await self.read_registers(
            address=self.point_address(point=point),
            count=point.len,
        )
        point.set_mb(data=read_bytes)
        return point.cvalue  # type: ignore[no-any-return]

    def point_address(
        self, point: sunspec2.modbus.client.SunSpecModbusClientPoint
    ) -> int:
        return point.model.model_addr + point.offset  # type: ignore[no-any-return]

    async def write_registers(self, address: int, values: bytes) -> None:
        if self.protocol is None:
            raise ssst.InvalidActionError("Cannot write without a managed connection.")

        response = await self.protocol.write_registers(
            address=address, values=values, unit=0x01
        )

        if isinstance(response, pymodbus.pdu.ExceptionResponse):
            raise ssst.ModbusError(exception=response)

    async def write_point(
        self, point: sunspec2.modbus.client.SunSpecModbusClientPoint
    ) -> None:
        if point.sf is not None:
            await self.read_point(point=point.model.points[point.sf])

        bytes_to_write = point.get_mb()
        await self.write_registers(
            address=self.point_address(point=point), values=bytes_to_write
        )
