import sys
from unittest import mock


def pytest_sessionstart(session):
    sys.modules["marker"] = mock.MagicMock()
    sys.modules["marker.convert"] = mock.MagicMock()
    sys.modules["marker.models"] = mock.MagicMock()
