"""Tool tests for DaVinci Resolve MCP — tests that work with or without Resolve."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from resolve_connection import _err, _ok, _ser


# ── Response format tests ──────────────────────────────────────────

def test_err_has_success_false():
    result = _err("test error")
    assert result["success"] is False
    assert result["error"] == "test error"


def test_ok_has_success_true():
    result = _ok(data="hello")
    assert result["success"] is True
    assert result["data"] == "hello"


def test_ok_multiple_kwargs():
    result = _ok(name="Timeline 1", index=1, tracks=3)
    assert result["success"] is True
    assert result["name"] == "Timeline 1"
    assert result["index"] == 1
    assert result["tracks"] == 3


# ── Serialization tests ───────────────────────────────────────────

def test_ser_nested_dict():
    data = {"a": {"b": [1, 2, {"c": "deep"}]}}
    result = _ser(data)
    assert result == {"a": {"b": [1, 2, {"c": "deep"}]}}


def test_ser_none():
    assert _ser(None) is None


def test_ser_object_with_getname():
    """Objects with GetName() should serialize to their name."""
    class FakeResolveObj:
        def GetName(self):
            return "MyProject"
    assert _ser(FakeResolveObj()) == "MyProject"


def test_ser_unknown_object():
    """Unknown objects should serialize to str()."""
    class Unknown:
        def __str__(self):
            return "<unknown>"
    assert _ser(Unknown()) == "<unknown>"


# ── JSON serializable responses ────────────────────────────────────

def test_err_is_json_serializable():
    result = _err("test")
    json.dumps(result)  # should not raise


def test_ok_is_json_serializable():
    result = _ok(names=["a", "b"], count=2, active=True)
    json.dumps(result)  # should not raise


# ── Integration tests (require Resolve) ────────────────────────────

def _resolve_available():
    """Check if Resolve is reachable."""
    try:
        from resolve_connection import ResolveConnection
        conn = ResolveConnection()
        return conn.connect() is not None
    except Exception:
        return False


class TestWithResolve:
    """Tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        from resolve_connection import ResolveConnection
        self.conn = ResolveConnection()

    def test_check_returns_project(self):
        pm, proj, err = self.conn.check()
        assert err is None
        assert pm is not None
        assert proj is not None
        assert proj.GetName()  # should return a string

    def test_get_media_pool_returns_pool(self):
        proj, mp, err = self.conn.get_media_pool()
        assert err is None
        assert mp is not None
        assert mp.GetCurrentFolder() is not None

    def test_get_timeline_when_none_active(self):
        """get_timeline may or may not return a timeline, but should not crash."""
        proj, tl, err = self.conn.get_timeline()
        # Either tl is valid or err explains why
        if tl is None:
            assert err is not None
            assert "timeline" in err["error"].lower()
        else:
            assert tl.GetName()


class TestFairlightWithResolve:
    """Audio/Fairlight tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import fairlight
        self.fairlight = fairlight

    def test_get_volume_missing_params(self):
        """get_volume ohne item_index gibt Fehler zurück."""
        result = self.fairlight(action="get_volume", track_index=1)
        assert result["success"] is False
        assert "item_index" in result["error"]

    def test_set_volume_missing_volume_param(self):
        """set_volume ohne volume-Parameter gibt Fehler zurück."""
        result = self.fairlight(action="set_volume", track_index=1, item_index=1)
        assert result["success"] is False
        assert "volume" in result["error"]

    def test_set_mute_missing_muted_param(self):
        """set_mute ohne muted-Parameter gibt Fehler zurück."""
        result = self.fairlight(action="set_mute", track_index=1)
        assert result["success"] is False
        assert "muted" in result["error"]

    def test_set_pan_out_of_range(self):
        """set_pan mit pan außerhalb -1.0..1.0 gibt Fehler zurück."""
        result = self.fairlight(action="set_pan", track_index=1, item_index=1, pan=2.5)
        assert result["success"] is False
        assert "1.0" in result["error"]

    def test_fade_in_missing_duration(self):
        """fade_in ohne duration gibt Fehler zurück."""
        result = self.fairlight(action="fade_in", track_index=1, item_index=1)
        assert result["success"] is False
        assert "duration" in result["error"]

    def test_fade_out_missing_duration(self):
        """fade_out ohne duration gibt Fehler zurück."""
        result = self.fairlight(action="fade_out", track_index=1, item_index=1)
        assert result["success"] is False
        assert "duration" in result["error"]


class TestTransitionWithResolve:
    """Transition tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import transition
        self.transition = transition

    def test_list_types_returns_known_types(self):
        """list_types gibt eine Liste bekannter Transition-Typen zurück."""
        result = self.transition(action="list_types")
        assert result["success"] is True
        assert "types" in result
        assert "Dissolve" in result["types"]
        assert "Cut" in result["types"]

    def test_add_missing_transition_type(self):
        """add ohne transition_type gibt Fehler zurück."""
        result = self.transition(
            action="add", track_type="video", track_index=1, item_index=1, duration=24
        )
        assert result["success"] is False
        assert "transition_type" in result["error"]

    def test_add_invalid_transition_type(self):
        """add mit unbekanntem transition_type gibt Fehler zurück."""
        result = self.transition(
            action="add", track_type="video", track_index=1, item_index=1,
            transition_type="UnknownFX", duration=24
        )
        assert result["success"] is False
        assert "UnknownFX" in result["error"]

    def test_add_missing_duration(self):
        """add ohne duration gibt Fehler zurück."""
        result = self.transition(
            action="add", track_type="video", track_index=1, item_index=1,
            transition_type="Dissolve"
        )
        assert result["success"] is False
        assert "duration" in result["error"]


class TestMarkerEditingWithResolve:
    """Marker-based editing tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import timeline
        self.timeline = timeline

    def test_get_marker_clips_returns_list(self):
        """get_marker_clips gibt success=True und eine clips-Liste zurück."""
        result = self.timeline(action="get_marker_clips")
        assert result["success"] is True
        assert "clips" in result
        assert isinstance(result["clips"], list)

    def test_split_at_markers_returns_summary(self):
        """split_at_markers gibt Anzahl erfolgreicher und fehlgeschlagener Splits zurück."""
        result = self.timeline(action="split_at_markers")
        assert result["success"] is True
        assert "splits_attempted" in result
        assert "splits_succeeded" in result
        assert "splits_failed" in result
