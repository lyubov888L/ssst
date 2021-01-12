import functools

import attr
import pymodbus.datastore
import pymodbus.device
import pymodbus.server.trio
import pymodbus.interfaces
import sunspec2.modbus.client


suns_marker = b"SunS"
base_address = 40_000


@attr.s(auto_attribs=True)
class ModelSummary:
    id: int
    length: int


def create_server_callable(model_summaries):
    address = len(suns_marker)
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
    server_context = pymodbus.datastore.ModbusServerContext(
        slaves=slave_context, single=True
    )
    identity = pymodbus.device.ModbusDeviceIdentification()

    return functools.partial(
        pymodbus.server.trio.tcp_server,
        context=server_context,
        identity=identity,
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
        data = bytearray(suns_marker)
        data.extend(all_registers)

        offset_address = requested_address - base_address

        return cls(
            data=data,
            slice=slice(2 * offset_address, 2 * (offset_address + count)),
            offset_address=offset_address,
            bytes_offset_address=2 * offset_address,
        )


@attr.s(auto_attribs=True)
class SunSpecModbusSlaveContext(pymodbus.interfaces.IModbusSlaveContext):
    sunspec_device: sunspec2.modbus.client.SunSpecModbusClientDevice
    """The valid range is exclusive of this address."""
    single: bool = attr.ib(default=True, init=False)

    def getValues(self, fx, address, count=1):
        request = PreparedRequest.build(
            base_address=self.sunspec_device.base_addr,
            requested_address=address,
            count=count,
            all_registers=self.sunspec_device.get_mb(),
        )
        return request.data[request.slice]

    def setValues(self, fx, address, values):
        request = PreparedRequest.build(
            base_address=self.sunspec_device.base_addr,
            requested_address=address,
            count=len(values),
            all_registers=self.sunspec_device.get_mb(),
        )
        data = bytearray(request.data)
        data[request.slice] = values
        self.sunspec_device.set_mb(data=data[len(suns_marker) :])

    def validate(self, fx, address, count=1):
        base_address = self.sunspec_device.base_addr
        end_address = base_address + (
            (len(suns_marker) + len(self.sunspec_device.get_mb())) / 2
        )
        return (
            self.sunspec_device.base_addr <= address and address + count <= end_address
        )
