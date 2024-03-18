from unittest.mock import MagicMock

import pytest


@pytest.fixture
def test_handler():
    return MagicMock()
