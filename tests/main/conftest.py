from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def disable_track():
    """Disables the track UI for running tests."""
    with patch("twyn.main.track") as m_track:
        m_track.side_effect = lambda iterable, description: iterable
        yield
