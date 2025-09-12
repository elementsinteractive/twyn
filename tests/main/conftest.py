from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def disable_track() -> Generator[None, Any, None]:
    """Disables the track UI for running tests."""
    with patch("rich.progress.track") as m_track:
        m_track.side_effect = lambda iterable, description: iterable
        yield
