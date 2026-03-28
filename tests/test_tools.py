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

    def test_delete_between_markers_missing_params(self):
        """delete_between_markers ohne marker_a_frame gibt Fehler zurück."""
        result = self.timeline(action="delete_between_markers")
        assert result["success"] is False
        assert "marker_a_frame" in result["error"]

    def test_rename_clips_from_markers_returns_summary(self):
        """rename_clips_from_markers gibt Anzahl umbenannter Clips zurück."""
        result = self.timeline(action="rename_clips_from_markers")
        assert result["success"] is True
        assert "renamed" in result
        assert isinstance(result["renamed"], int)


class TestTimelinePlayheadWithResolve:
    """Playhead control tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import timeline
        self.timeline = timeline

    def test_get_timecode_returns_timecode(self):
        """get_timecode gibt einen Timecode-String zurück."""
        result = self.timeline(action="get_timecode")
        assert result["success"] is True
        assert "timecode" in result
        assert ":" in result["timecode"]

    def test_set_timecode_missing_name(self):
        """set_timecode ohne name gibt Fehler zurück."""
        result = self.timeline(action="set_timecode")
        assert result["success"] is False
        assert "timecode" in result["error"].lower()

    def test_set_timecode_invalid_format(self):
        """set_timecode mit ungültigem Format gibt Fehler zurück."""
        result = self.timeline(action="set_timecode", name="invalid")
        assert result["success"] is False
        assert "format" in result["error"].lower()


class TestTimelineItemTakesWithResolve:
    """Take management tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import timeline_item
        self.timeline_item = timeline_item

    def test_get_takes_returns_list(self):
        """get_takes gibt count und takes-Liste zurück."""
        result = self.timeline_item(action="get_takes", track_type="video", track_index=1, item_index=0)
        assert result["success"] is True
        assert "count" in result
        assert "takes" in result

    def test_get_selected_take_returns_index(self):
        """get_selected_take gibt selected_take zurück."""
        result = self.timeline_item(action="get_selected_take", track_type="video", track_index=1, item_index=0)
        assert result["success"] is True
        assert "selected_take" in result

    def test_add_take_missing_media_pool_clip(self):
        """add_take ohne media_pool_clip gibt Fehler zurück."""
        result = self.timeline_item(action="add_take", track_type="video", track_index=1, item_index=0)
        assert result["success"] is False
        assert "media_pool_clip" in result["error"]

    def test_select_take_missing_take_index(self):
        """select_take ohne take_index gibt Fehler zurück."""
        result = self.timeline_item(action="select_take", track_type="video", track_index=1, item_index=0)
        assert result["success"] is False
        assert "take_index" in result["error"]

    def test_delete_take_missing_take_index(self):
        """delete_take ohne take_index gibt Fehler zurück."""
        result = self.timeline_item(action="delete_take", track_type="video", track_index=1, item_index=0)
        assert result["success"] is False
        assert "take_index" in result["error"]

    def test_finalize_take_returns_result(self):
        """finalize_take gibt finalized-Status zurück."""
        result = self.timeline_item(action="finalize_take", track_type="video", track_index=1, item_index=0)
        assert result["success"] is True
        assert "finalized" in result


class TestTimelineItemCacheWithResolve:
    """Cache/sidecar/stabilize tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import timeline_item
        self.timeline_item = timeline_item

    def test_get_cache_returns_status(self):
        """get_cache gibt color_cache und fusion_cache zurück."""
        result = self.timeline_item(action="get_cache", track_type="video", track_index=1, item_index=0)
        assert result["success"] is True
        assert "color_cache" in result
        assert "fusion_cache" in result

    def test_set_cache_missing_cache_type(self):
        """set_cache ohne cache_type gibt Fehler zurück."""
        result = self.timeline_item(
            action="set_cache", track_type="video", track_index=1, item_index=0,
            property_value="true"
        )
        assert result["success"] is False
        assert "cache_type" in result["error"]

    def test_set_cache_invalid_cache_type(self):
        """set_cache mit ungültigem cache_type gibt Fehler zurück."""
        result = self.timeline_item(
            action="set_cache", track_type="video", track_index=1, item_index=0,
            cache_type="invalid", property_value="true"
        )
        assert result["success"] is False
        assert "color" in result["error"] or "fusion" in result["error"]

    def test_update_sidecar_returns_result(self):
        """update_sidecar gibt updated-Status zurück."""
        result = self.timeline_item(action="update_sidecar", track_type="video", track_index=1, item_index=0)
        assert result["success"] is True
        assert "updated" in result

    def test_stabilize_returns_result(self):
        """stabilize gibt stabilized-Status zurück."""
        result = self.timeline_item(action="stabilize", track_type="video", track_index=1, item_index=0)
        assert result["success"] is True
        assert "stabilized" in result


class TestColorVersionsWithResolve:
    """Color version tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import color
        self.color = color

    def test_list_versions_returns_list(self):
        """list_versions gibt versions-Liste zurück."""
        result = self.color(action="list_versions")
        assert result["success"] is True
        assert "versions" in result
        assert isinstance(result["versions"], list)

    def test_get_version_returns_info(self):
        """get_version gibt version-Info zurück."""
        result = self.color(action="get_version")
        assert result["success"] is True
        assert "version" in result

    def test_add_version_missing_name(self):
        """add_version ohne version_name gibt Fehler zurück."""
        result = self.color(action="add_version")
        assert result["success"] is False
        assert "version_name" in result["error"]

    def test_load_version_missing_name(self):
        """load_version ohne version_name gibt Fehler zurück."""
        result = self.color(action="load_version")
        assert result["success"] is False
        assert "version_name" in result["error"]

    def test_delete_version_missing_name(self):
        """delete_version ohne version_name gibt Fehler zurück."""
        result = self.color(action="delete_version")
        assert result["success"] is False
        assert "version_name" in result["error"]


class TestColorMagicMaskWithResolve:
    """Magic mask and LUT export tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import color
        self.color = color

    def test_create_magic_mask_missing_mode(self):
        """create_magic_mask ohne lut_path (mode) gibt Fehler zurück."""
        result = self.color(action="create_magic_mask")
        assert result["success"] is False
        assert "mode" in result["error"].lower() or "lut_path" in result["error"]

    def test_create_magic_mask_invalid_mode(self):
        """create_magic_mask mit ungültigem Mode gibt Fehler zurück."""
        result = self.color(action="create_magic_mask", lut_path="X")
        assert result["success"] is False
        assert "F" in result["error"] or "mode" in result["error"].lower()

    def test_export_lut_missing_path(self):
        """export_lut ohne lut_path gibt Fehler zurück."""
        result = self.color(action="export_lut", node_index=0)
        assert result["success"] is False
        assert "lut_path" in result["error"]

    def test_export_lut_missing_node_index(self):
        """export_lut ohne node_index gibt Fehler zurück."""
        result = self.color(action="export_lut", lut_path="/tmp/test.cube")
        assert result["success"] is False
        assert "node_index" in result["error"]


class TestFairlightVoiceIsolationWithResolve:
    """Voice isolation and audio mapping tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import fairlight
        self.fairlight = fairlight

    def test_get_voice_isolation_missing_params(self):
        """get_voice_isolation ohne track_index gibt Fehler zurück."""
        result = self.fairlight(action="get_voice_isolation")
        assert result["success"] is False
        assert "track_index" in result["error"]

    def test_set_voice_isolation_missing_params(self):
        """set_voice_isolation ohne track_index gibt Fehler zurück."""
        result = self.fairlight(action="set_voice_isolation")
        assert result["success"] is False
        assert "track_index" in result["error"]

    def test_set_voice_isolation_amount_out_of_range(self):
        """set_voice_isolation mit amount > 100 gibt Fehler zurück."""
        result = self.fairlight(
            action="set_voice_isolation", track_index=1, item_index=1,
            enabled=True, amount=150
        )
        assert result["success"] is False
        assert "100" in result["error"]

    def test_get_audio_mapping_missing_params(self):
        """get_audio_mapping ohne track_index gibt Fehler zurück."""
        result = self.fairlight(action="get_audio_mapping")
        assert result["success"] is False
        assert "track_index" in result["error"]
