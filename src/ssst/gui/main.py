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


default_exception_dialog_title = "Unhandled Exception"


@attr.s(auto_attribs=True)
class ExceptionPresenter:
    """A context manager that will handle exceptions by presenting them in a dialog."""

    title: str = default_exception_dialog_title
    """The window title for the exception dialog to be shown in the title bar."""
    parent: typing.Optional[QtWidgets.QWidget] = None
    """The parent for the dialog.  For example, the dialog may be centered on its
    parent or may be modal and block access to its parent.
    """
    exceptions: typing.Union[
        typing.Type[Exception], typing.Tuple[typing.Type[Exception], ...]
    ] = Exception
    """The exception or exceptions to be caught and handled."""
    message_box: typing.Optional[qtrio.dialogs.MessageBox] = None
    """The dialog widget itself."""

    # TODO: Make this act as `message_box_shown`?  Also maybe refer to it as the
    #       dialog.
    message_box_created = qtrio.Signal()
    """Emitted when the dialog is created.  Note that it is not shown until slightly
    later.
    """

    @async_generator.asynccontextmanager
    async def manage(self) -> typing.AsyncIterator[None]:
        """Capture an instance of the configured exceptions if raised within the
        context and present it in a dialog.
        """
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


@async_generator.asynccontextmanager
async def present_and_consume_exceptions(
    title: str = default_exception_dialog_title,
    parent: typing.Optional[QtWidgets.QWidget] = None,
    exceptions: typing.Union[
        typing.Type[Exception], typing.Tuple[typing.Type[Exception], ...]
    ] = Exception,
) -> typing.AsyncIterator[ExceptionPresenter]:
    """Directly create and enter an exception handling and presenting context
    implemented by :class:`ExceptionPresenter`.
    """
    presenter = ExceptionPresenter(title=title, parent=parent, exceptions=exceptions)

    async with presenter.manage():
        yield presenter


class SignaledMainWindow(QtWidgets.QMainWindow):
    """Adds ``closed`` and ``shown`` signals to a :class:`QtWidgets.QMainWindow`."""

    closed: QtCore.Signal = QtCore.Signal()
    """Emitted by an accepted :class:`QtGui.QCloseEvent`."""
    shown: QtCore.Signal = QtCore.Signal()
    """Emitted by an accepted :class:`QtGui.QShowEvent`."""

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
    """Fill the gap since Trio doesn't provide type hints for the task status objects
    discussed in :meth:`trio.Nursery.start`.
    """

    def started(self, item: object) -> None:
        ...


@attr.s(auto_attribs=True)
class Window:
    """The main SSST window."""

    _title: str
    """The window title.  The title is only set when initiating :meth:`Window.run`, not
    anytime this attribute is assigned to.
    """
    widget: SignaledMainWindow = attr.ib(factory=SignaledMainWindow)
    """The actual Qt widget instance of the window."""
    ui: ssst.gui.main_ui.Ui_MainWindow = attr.ib(factory=ssst.gui.main_ui.Ui_MainWindow)
    """The UI elements are stored in this attribute giving them a namespace which is
    separated from the code for the class."""
    emissions_exception_presenter: ExceptionPresenter = ExceptionPresenter()
    """The exception presenter used while handling emissions.  Generally only useful
    for testing purposes.
    """
    _has_run: bool = attr.ib(default=False, init=False)
    """This widget is not rerunnable.  Track if it has been run and complain if it is
    reused.
    """

    async def raise_clicked(self) -> None:
        """Just an initial method for exploring patterns and exception handling."""

        raise Exception("This is a demonstration exception to show off its handling.")

    async def run(
        self, *, task_status: TaskStatusProtocol = trio.TASK_STATUS_IGNORED
    ) -> None:
        """Run the window.  If :meth:`trio.Nursery.start` is used to launch the task
        then it will indicate it has started after the widget has been shown.

        Arguments:
            task_status: Generally passed by :meth:`trio.Nursery.start`, and otherwise
                unspecified.
        """
        if self._has_run:
            raise ssst.ReuseError(cls=type(self))
        self._has_run = True

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
                if debug_file_variable is not None:  # pragma: no cover
                    # TODO: This is generally actually covered by
                    #       ssst._tests.test_cli.test_gui_persists but the coverage
                    #       recording or reporting isn't working out.
                    #       https://github.com/altendky/ssst/issues/13
                    debug_path = pathlib.Path(debug_file_variable)
                    debug_text = os.environ["SSST_DEBUG_BYTES"]
                    debug_path.write_bytes(os.fsencode(debug_text))

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
        """
        Creates and runs the window.  If :meth:`trio.Nursery.start` is used to launch
        the task then it will indicate it has started after the widget has been shown.

        Arguments:
            title: The window title.
            task_status: Generally passed by :meth:`trio.Nursery.start`, and otherwise
                unspecified.
        """

        async with present_and_consume_exceptions():
            async with trio.open_nursery() as nursery:
                instance = cls(title=title)

                instance.emissions_exception_presenter.title = title
                instance.emissions_exception_presenter.parent = instance.widget

                await nursery.start(instance.run)

                task_status.started(instance)
