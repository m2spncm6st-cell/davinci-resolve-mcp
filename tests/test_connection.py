"""Connection tests for DaVinci Resolve MCP."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resolve_connection import ResolveConnection


def test_connection_object_creates():
    """ResolveConnection can be instantiated without Resolve running."""
    conn = ResolveConnection()
    assert conn is not None
    assert conn._resolve is None


def test_disconnect():
    """Disconnect clears cached state."""
    conn = ResolveConnection()
    conn.disconnect()
    assert conn._resolve is None
    assert conn._last_check == 0
