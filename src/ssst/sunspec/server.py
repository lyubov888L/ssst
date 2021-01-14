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
    """A model can be summarized by its ID and length.  While models of fixed length
    would not need the length provided, those with repeatable blocks need a length to
    indicate the number of repetitions of the repeating block."""

    id: int
    """The integer model ID."""
    length: int
    """The model length inclusive of the fixed and repeating blocks and exclusive of
    the model's ID and length header."""


@attr.s(auto_attribs=True)
class SunSpecModbusSlaveContext(pymodbus.interfaces.IModbusSlaveContext):
    """A :mod:`pymodbus` slave context that is backed by the ``pysunspec2`` device
    object."""

    sunspec_device: sunspec2.modbus.client.SunSpecModbusClientDevice
    """The ``pysunspec2`` device object use for local storage of the SunSpec data."""

    def getValues(self, fx: int, address: int, count: int = 1) -> bytearray:
        """See :meth:`pymodbus.interfaces.IModbusSlaveContext.getValues`."""
        request = PreparedRequest.build(
            base_address=self.sunspec_device.base_addr,
            requested_address=address,
            count=count,
            all_registers=self.sunspec_device.get_mb(),
        )
        return request.data[request.slice]

    def setValues(self, fx: int, address: int, values: bytes) -> None:
        """See :meth:`pymodbus.interfaces.IModbusSlaveContext.setValues`."""
        request = PreparedRequest.build(
            base_address=self.sunspec_device.base_addr,
            requested_address=address,
            count=len(values) // 2,
            all_registers=self.sunspec_device.get_mb(),
        )
        data = bytearray(request.data)
        data[request.slice] = values
        self.sunspec_device.set_mb(data=data[len(ssst.sunspec.base_address_sentinel) :])

    def validate(self, fx: int, address: int, count: int = 1) -> bool:
        """See :meth:`pymodbus.interfaces.IModbusSlaveContext.validate`."""
        return (
            self.sunspec_device.base_addr <= address
            and address + count <= self._end_address()
        )

    def _end_address(self) -> int:
        """Calculate the exclusive last address.  This is the first address which
        cannot be read.
        """
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
    """A SunSpec Modbus TCP server using :mod:`trio` support in :mod:`pymodbus` for
    communication and `pysunspec2` for loading models and holding the local cache of
    the data.  The actual TCP server can be launched using :meth:`Server.tcp_server`.

    .. code-block:: python

        await nursery.start(
            functools.partial(
                trio.serve_tcp,
                server.tcp_server,
                host="127.0.0.1",
                port=0,
            ),
        )

    .. automethod:: __getitem__
    """

    slave_context: SunSpecModbusSlaveContext
    """The single slave context to be served by this server.  This is backed by the
    SunSpec device object.
    """
    server_context: pymodbus.datastore.ModbusServerContext
    """The datastore for this pymodbus server.  Presently only a single slave context
    is supported."""
    identity: pymodbus.device.ModbusDeviceIdentification
    """The identity information for this Modbus server."""

    @classmethod
    def build(cls, model_summaries: typing.Sequence[ModelSummary]) -> "Server":
        """Build the server instance based on the passed model summaries.  Any
        per-point or bulk data update must be done separately.

        Arguments:
            model_summaries: The models which you want the server to provide.

        Returns:
            The instance of the server datastore pieces.
        """
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
        """SunSpec models are accessible by indexing the client using either the model
        number or model name.

        .. code-block:: python

            model_1 = server[1]
            model_common = server["common"]
            assert model_1 is model_common

        Arguments:
            item: The integer or string identifying the model.
        Returns:
            The requested model.
        """
        [model] = self.slave_context.sunspec_device.models[item]
        return model

    async def tcp_server(self, server_stream: trio.SocketStream) -> None:
        """Handle serving over a stream.  See :class:`Server` for an example.

        Arguments:
            server_stream: The stream to communicate over.
        """

        await pymodbus.server.trio.tcp_server(
            server_stream=server_stream,
            context=self.server_context,
            identity=self.identity,
        )


@attr.s(auto_attribs=True)
class PreparedRequest:
    """Holds some common bits used in serving a request."""

    data: bytearray
    """The entire block of registers.  Each register is a 2-byte chunk stored in
    big-endian byte order.  The first element is the high byte of the server's register
    located at the base address.
    """
    slice: slice
    """The slice covering the bytes of the registers to be operated on."""
    offset_address: int
    """The offset in 16-bit/2-byte registers relative to the server's base address."""
    bytes_offset_address: int
    """The offset in bytes relative to the server's base address."""

    @classmethod
    def build(
        cls, base_address: int, requested_address: int, count: int, all_registers: bytes
    ) -> "PreparedRequest":
        """Build the instance based on the passed raw request information.

        Arguments:
            base_address: The SunSpec base register address.
            requested_address: The requested address.
            count: The requested register count.
            all_registers: The raw register data for all models.

        Returns:
            The prepared request information.
        """
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
