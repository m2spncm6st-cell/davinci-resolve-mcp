"""Connection tests for DaVinci Resolve MCP."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resolve_connection import ResolveConnection, _err, _ok, _ser


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


def test_err_format():
    """_err returns standardized error dict."""
    result = _err("something went wrong")
    assert result == {"success": False, "error": "something went wrong"}


def test_ok_format():
    """_ok returns standardized success dict."""
    result = _ok(version="20.3.1", page="edit")
    assert result == {"success": True, "version": "20.3.1", "page": "edit"}


def test_ser_primitives():
    """_ser passes through primitive types."""
    assert _ser("hello") == "hello"
    assert _ser(42) == 42
    assert _ser(3.14) == 3.14
    assert _ser(True) is True
    assert _ser(None) is None


def test_ser_collections():
    """_ser handles dicts and lists."""
    assert _ser({"a": 1, "b": [2, 3]}) == {"a": 1, "b": [2, 3]}
    assert _ser([1, "two", None]) == [1, "two", None]


def test_check_returns_tuple():
    """check() returns a 3-tuple regardless of connection state."""
    conn = ResolveConnection()
    result = conn.check()
    assert len(result) == 3
    pm, proj, err = result
    # Either connected (err is None, pm+proj not None)
    # or not connected (err is a dict with success=False)
    if err is not None:
        assert err["success"] is False
    else:
        assert pm is not None


def test_get_media_pool_returns_tuple():
    """get_media_pool() returns a 3-tuple."""
    conn = ResolveConnection()
    result = conn.get_media_pool()
    assert len(result) == 3


def test_get_timeline_returns_tuple():
    """get_timeline() returns a 3-tuple."""
    conn = ResolveConnection()
    result = conn.get_timeline()
    assert len(result) == 3
