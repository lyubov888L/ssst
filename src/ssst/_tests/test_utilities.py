import pytest
import _pytest.pytester
import qtpy

import ssst._utilities


def test_qt_api_environment_variable_name() -> None:
    assert qtpy.QT_API == ssst._utilities.qt_api_variable_name


def test_configure_qtpy_raises(pytester: _pytest.pytester.Pytester) -> None:
    content = f"""
    import os
    import sys

    import pytest

    import ssst._utilities
    import ssst.exceptions


    os.environ.pop(ssst._utilities.qt_api_variable_name)


    def test():
        import qtpy

        with pytest.raises(ssst.exceptions.QtpyError, match="qtpy imported prior to"):
            ssst._utilities.configure_qtpy(
                api=ssst._utilities.QtApis.PyQt5,
            )
    """
    pytester.makepyfile(content)
    run_result = pytester.runpytest_subprocess()
    run_result.assert_outcomes(passed=1)


def test_configure_qtpy_does_not_import(pytester: _pytest.pytester.Pytester) -> None:
    content = f"""
    import os
    import sys

    import pytest

    import ssst._utilities


    os.environ.pop(ssst._utilities.qt_api_variable_name)


    def test():
        ssst._utilities.configure_qtpy(api=ssst._utilities.QtApis.PyQt5)

        assert "qtpy" not in sys.modules
    """
    pytester.makepyfile(content)
    run_result = pytester.runpytest_subprocess()
    run_result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    argnames=["api_string", "api"],
    argvalues=[[api.value, api] for api in ssst._utilities.QtApis],
)
def test_configure_qtpy_sets_requested_api(
    pytester: _pytest.pytester.Pytester,
    api_string: str,
    api: ssst._utilities.QtApis,
) -> None:
    content = f"""
    import os
    import sys

    import ssst._utilities

    os.environ.pop(ssst._utilities.qt_api_variable_name)

    
    def test():
        assert 'qtpy' not in sys.modules

        ssst._utilities.configure_qtpy(
            api=ssst._utilities.QtApis({api_string!r}),
        )

        assert "qtpy" not in sys.modules

        import qtpy

        assert qtpy.API == {api.value!r}
    """
    pytester.makepyfile(content)
    run_result = pytester.runpytest_subprocess()
    run_result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    argnames=["api"],
    argvalues=[[api] for api in ssst._utilities.QtApis],
)
def test_configure_qtpy_handles_env_var(
    pytester: _pytest.pytester.Pytester,
    api: ssst._utilities.QtApis,
) -> None:
    content = f"""
    import os
    import sys

    import ssst._utilities

    os.environ[ssst._utilities.qt_api_variable_name] = {api.value!r}


    def test():
        assert 'qtpy' not in sys.modules

        ssst._utilities.configure_qtpy(api=42)

        assert "qtpy" not in sys.modules

        import qtpy

        assert qtpy.API == {api.value!r}
    """
    pytester.makepyfile(content)
    run_result = pytester.runpytest_subprocess()
    run_result.assert_outcomes(passed=1)
