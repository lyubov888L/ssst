import typing

import qtrio

import ssst


def test_unexpected_emission_error_text():
    # close enough to an emission for now
    item = typing.cast(qtrio.Emission, object())

    error = ssst.UnexpectedEmissionError(emission=item)

    assert str(error) == f"Unexpected emission: {item!r}"
