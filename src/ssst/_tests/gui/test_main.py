import functools

import pytest
import trio

import ssst.gui.main


async def test_widget_is_shown_before_starting(nursery):
    main_window: ssst.gui.main.Window = await nursery.start(
        functools.partial(ssst.gui.main.Window.start, title="")
    )

    assert main_window.widget.isVisible()


async def test_start_ends_when_closed():
    async with trio.open_nursery() as nursery:
        main_window: ssst.gui.main.Window = await nursery.start(
            functools.partial(ssst.gui.main.Window.start, title="SSST")
        )

        main_window.widget.close()


async def test_start_sets_window_title(nursery):
    title = "some Unique other 1234 Title"

    main_window: ssst.gui.main.Window = await nursery.start(
        functools.partial(ssst.gui.main.Window.start, title=title)
    )

    assert main_window.widget.windowTitle() == title


async def test_emissions_exception_shows_dialog(nursery):
    main_window: ssst.gui.main.Window = await nursery.start(
        functools.partial(ssst.gui.main.Window.start, title="title")
    )

    # TODO: uh...  private?
    import qtrio._core

    async with qtrio._core.wait_signal_context(
        signal=main_window.emissions_exception_presenter.message_box_created
    ):
        main_window.ui.raise_button.click()

    assert main_window.emissions_exception_presenter.message_box is not None


async def test_window_reuse_raises(nursery):
    window = await nursery.start(
        functools.partial(ssst.gui.main.Window.start, title="")
    )
    window.widget.close()

    with pytest.raises(ssst.ReuseError, match=str(ssst.gui.main.Window)):
        await window.run()
