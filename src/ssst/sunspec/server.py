import functools
import typing

import attr
import pymodbus.datastore
import pymodbus.device
import pymodbus.server.trio
import pymodbus.interfaces
import sunspec2.mb
import sunspec2.modbus.client
import trio

import ssst.sunspec


base_address = 40_000


@attr.s(auto_attribs=True)
class ModelSummary:
    id: int
    length: int


@attr.s(auto_attribs=True)
class SunSpecModbusSlaveContext(pymodbus.interfaces.IModbusSlaveContext):
    sunspec_device: sunspec2.modbus.client.SunSpecModbusClientDevice
    """The valid range is exclusive of this address."""
    single: bool = attr.ib(default=True, init=False)

    def getValues(self, fx: int, address: int, count: int = 1) -> bytearray:
        request = PreparedRequest.build(
            base_address=self.sunspec_device.base_addr,
            requested_address=address,
            count=count,
            all_registers=self.sunspec_device.get_mb(),
        )
        return request.data[request.slice]

    def setValues(self, fx: int, address: int, values: bytes) -> None:
        request = PreparedRequest.build(
            base_address=self.sunspec_device.base_addr,
            requested_address=address,
            count=len(values),
            all_registers=self.sunspec_device.get_mb(),
        )
        data = bytearray(request.data)
        data[request.slice] = values
        self.sunspec_device.set_mb(data=data[len(ssst.sunspec.base_address_sentinel) :])

    def validate(self, fx: int, address: int, count: int = 1) -> bool:
        return (
            self.sunspec_device.base_addr <= address
            and address + count <= self.end_address()
        )

    def end_address(self) -> int:
        return (
            base_address
            + (
                (
                    len(ssst.sunspec.base_address_sentinel)
                    + len(self.sunspec_device.get_mb())
                )
                // 2
            )
            + 2
        )


@attr.s(auto_attribs=True)
class Server:
    slave_context: SunSpecModbusSlaveContext
    server_context: pymodbus.datastore.ModbusServerContext
    identity: pymodbus.device.ModbusDeviceIdentification

    @classmethod
    def build(cls, model_summaries: typing.Sequence[ModelSummary]) -> "Server":
        address = base_address + len(ssst.sunspec.base_address_sentinel) // 2
        sunspec_device = sunspec2.modbus.client.SunSpecModbusClientDevice()
        sunspec_device.base_addr = base_address

        for model_summary in model_summaries:
            model = sunspec2.modbus.client.SunSpecModbusClientModel(
                model_id=model_summary.id,
                model_addr=address,
                model_len=model_summary.length,
                mb_device=sunspec_device,
            )
            address += 2 + model_summary.length
            sunspec_device.add_model(model)

        slave_context = SunSpecModbusSlaveContext(sunspec_device=sunspec_device)

        return cls(
            slave_context=slave_context,
            server_context=pymodbus.datastore.ModbusServerContext(
                slaves=slave_context,
                single=True,
            ),
            identity=pymodbus.device.ModbusDeviceIdentification(),
        )

    def __getitem__(
        self, item: typing.Union[int, str]
    ) -> sunspec2.modbus.client.SunSpecModbusClientModel:
        [model] = self.slave_context.sunspec_device.models[item]
        return model

    async def tcp_server(self, server_stream: trio.SocketStream) -> None:
        await pymodbus.server.trio.tcp_server(
            server_stream=server_stream,
            context=self.server_context,
            identity=self.identity,
        )


@attr.s(auto_attribs=True)
class PreparedRequest:
    data: bytearray
    slice: slice
    offset_address: int
    bytes_offset_address: int

    @classmethod
    def build(
        cls, base_address: int, requested_address: int, count: int, all_registers: bytes
    ) -> "PreparedRequest":  # TODO: should this be a TypeVar?
        # This is super lazy, what with building _all_ data even if you only need a
        # register or two.  But, optimize when we need to.
        data = bytearray(ssst.sunspec.base_address_sentinel)
        data.extend(all_registers)
        data.extend(
            sunspec2.mb.SUNS_END_MODEL_ID.to_bytes(
                length=2, byteorder="big", signed=False
            )
        )

        offset_address = requested_address - base_address

        return cls(
            data=data,
            slice=slice(2 * offset_address, 2 * (offset_address + count)),
            offset_address=offset_address,
            bytes_offset_address=2 * offset_address,
        )
