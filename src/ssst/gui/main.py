import contextlib
import os
import pathlib
import sys
import traceback
import typing

import async_generator
import attr
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
import qtrio._core  # TODO: uh...  private?
import qtrio.dialogs
import trio
import typing_extensions

import ssst.gui.main_ui


@attr.s(auto_attribs=True)
class ExceptionPresenter:
    title: str = "Unhandled Exception"
    parent: typing.Optional[QtWidgets.QWidget] = None
    exceptions: typing.Union[
        typing.Type[Exception], typing.Tuple[typing.Type[Exception], ...]
    ] = Exception
    message_box: typing.Optional[qtrio.dialogs.MessageBox] = None

    message_box_created = qtrio.Signal()

    @async_generator.asynccontextmanager
    async def manage(self) -> typing.AsyncIterator[None]:
        try:
            yield
        except self.exceptions:
            text = traceback.format_exc()
            self.message_box = qtrio.dialogs.create_message_box(
                title=self.title,
                text=text,
                parent=self.parent,
            )
            try:
                self.message_box_created.emit()
                sys.stderr.write(text)

                await self.message_box.wait()
            finally:
                self.message_box = None


class SignaledMainWindow(QtWidgets.QMainWindow):
    closed = QtCore.Signal()
    shown = QtCore.Signal()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Detect close events and emit the ``closed`` signal."""

        super().closeEvent(event)
        if event.isAccepted():
            self.closed.emit()
        else:  # pragma: no cover
            pass

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """Detect show events and emit the ``shown`` signal."""

        super().showEvent(event)
        if event.isAccepted():
            self.shown.emit()
        else:  # pragma: no cover
            pass


class TaskStatusProtocol(typing_extensions.Protocol):
    def started(self, item: object) -> None:
        ...


@attr.s(auto_attribs=True)
class Window:
    _title: str
    widget: SignaledMainWindow = attr.ib(factory=SignaledMainWindow)
    ui: ssst.gui.main_ui.Ui_MainWindow = attr.ib(factory=ssst.gui.main_ui.Ui_MainWindow)
    emissions_exception_presenter: ExceptionPresenter = ExceptionPresenter()

    async def raise_clicked(self) -> None:
        raise Exception("This is a demonstration exception to show off its handling.")

    async def run(
        self, *, task_status: TaskStatusProtocol = trio.TASK_STATUS_IGNORED
    ) -> None:
        self.ui.setupUi(MainWindow=self.widget)  # type: ignore[no-untyped-call]
        self.widget.setWindowTitle(self._title)

        with contextlib.closing(self.widget):
            async with qtrio.enter_emissions_channel(
                signals=[self.ui.raise_button.clicked, self.widget.closed]
            ) as emissions:
                # TODO: uh...  private?
                async with qtrio._core.wait_signal_context(
                    signal=self.widget.shown,
                ):
                    self.widget.show()

                task_status.started(self)

                # TODO: this should be replaced with logging which the test checks
                debug_file_variable = os.environ.get("SSST_DEBUG_FILE", None)
                if debug_file_variable is not None:
                    debug_path = pathlib.Path(debug_file_variable)
                    debug_path.write_bytes(os.environb[b"SSST_DEBUG_BYTES"])

                async for emission in emissions.channel:
                    async with self.emissions_exception_presenter.manage():
                        if emission.is_from(signal=self.ui.raise_button.clicked):
                            await self.raise_clicked()
                        elif emission.is_from(signal=self.widget.closed):
                            break
                        else:
                            raise ssst.UnexpectedEmissionError(emission)

    @classmethod
    async def start(
        cls, title: str, *, task_status: TaskStatusProtocol = trio.TASK_STATUS_IGNORED
    ) -> None:
        exception_presenter = ExceptionPresenter()

        async with exception_presenter.manage():
            async with trio.open_nursery() as nursery:
                instance = cls(title=title)

                instance.emissions_exception_presenter.title = title
                instance.emissions_exception_presenter.parent = instance.widget

                await nursery.start(instance.run)

                task_status.started(instance)
