"""Stability and integration tests for DaVinci Resolve MCP.

These tests validate the complete tool chain against a running Resolve instance.
Skip automatically if Resolve is not available.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resolve_connection import ResolveConnection, _err, _ok, _ser


def _resolve_available():
    try:
        conn = ResolveConnection()
        return conn.connect() is not None
    except Exception:
        return False


class TestResolveStability:
    """Stability tests requiring a running Resolve instance."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        self.conn = ResolveConnection()

    def test_reconnect_uses_cache(self):
        """Second connect() call uses cache, not a fresh connection."""
        r1 = self.conn.connect()
        t1 = self.conn._last_check
        r2 = self.conn.connect()
        t2 = self.conn._last_check
        assert r1 is r2
        assert t1 == t2  # no re-check within interval

    def test_health_check_after_interval(self):
        """After check_interval, health check runs again."""
        self.conn.connect()
        self.conn._last_check = 0  # force re-check
        r = self.conn.connect()
        assert r is not None
        assert self.conn._last_check > 0

    def test_disconnect_and_reconnect(self):
        """Can disconnect and reconnect."""
        self.conn.connect()
        self.conn.disconnect()
        assert self.conn._resolve is None
        r = self.conn.connect()
        assert r is not None

    def test_page_navigation_roundtrip(self):
        """Can navigate to all pages and back."""
        r = self.conn.connect()
        original = r.GetCurrentPage()
        for page in ("media", "edit", "color"):
            assert r.OpenPage(page)
            time.sleep(0.2)
        # Return to original
        r.OpenPage(original or "edit")

    def test_project_list_not_empty(self):
        """There should be at least one project."""
        r = self.conn.connect()
        pm = r.GetProjectManager()
        projects = pm.GetProjectListInCurrentFolder()
        assert len(projects) > 0

    def test_media_pool_accessible(self):
        """MediaPool should be accessible."""
        proj, mp, err = self.conn.get_media_pool()
        assert err is None
        folder = mp.GetCurrentFolder()
        assert folder is not None
        assert folder.GetName()

    def test_render_formats_available(self):
        """Render formats should be retrievable."""
        pm, proj, err = self.conn.check()
        assert err is None
        formats = proj.GetRenderFormats()
        assert isinstance(formats, dict)
        assert len(formats) > 0

    def test_ser_handles_resolve_objects(self):
        """_ser should handle real Resolve API objects."""
        pm, proj, err = self.conn.check()
        assert err is None
        # GetRenderFormats returns a dict of strings
        formats = proj.GetRenderFormats()
        result = _ser(formats)
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result.keys())
