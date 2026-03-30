import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import LOOKS, TRANSITIONS, _cdl_str


def test_looks_has_12_presets():
    assert len(LOOKS) == 12


def test_each_look_has_required_keys():
    for name, look in LOOKS.items():
        assert "description" in look, f"{name} missing description"
        assert "Slope" in look, f"{name} missing Slope"
        assert "Offset" in look, f"{name} missing Offset"
        assert "Power" in look, f"{name} missing Power"
        assert "Saturation" in look, f"{name} missing Saturation"


def test_each_look_cdl_values_are_strings():
    for name, look in LOOKS.items():
        for key in ("Slope", "Offset", "Power"):
            assert isinstance(look[key], str), f"{name}.{key} must be str"
            parts = look[key].split()
            assert len(parts) == 3, f"{name}.{key} must have 3 components"
        assert isinstance(look["Saturation"], str), f"{name}.Saturation must be str"


def test_transitions_has_6_types():
    assert len(TRANSITIONS) == 6


def test_each_transition_has_required_keys():
    for name, t in TRANSITIONS.items():
        assert "description" in t, f"{name} missing description"
        assert "filename" in t, f"{name} missing filename"


def test_cdl_str_formats_float():
    assert _cdl_str(1.0, 1.0, 1.0) == "1.000 1.000 1.000"


def test_cdl_str_formats_asymmetric():
    assert _cdl_str(1.1, 0.95, 0.88) == "1.100 0.950 0.880"


def test_build_cdl_dict_has_node_index():
    from server import _build_cdl_dict
    result = _build_cdl_dict(LOOKS["cinematic_teal_orange"])
    assert result["NodeIndex"] == "1"
    assert "Slope" in result
    assert "Offset" in result
    assert "Power" in result
    assert "Saturation" in result


def test_build_cdl_dict_values_match_look():
    from server import _build_cdl_dict
    look = LOOKS["aerial_clean"]
    result = _build_cdl_dict(look)
    assert result["Slope"] == look["Slope"]
    assert result["Saturation"] == look["Saturation"]


def test_apply_look_unknown_look_returns_error():
    from unittest.mock import MagicMock, patch
    import server

    mock_item = MagicMock()
    mock_item.SetCDL.return_value = True
    mock_tl = MagicMock()
    mock_tl.GetCurrentVideoItem.return_value = mock_item
    mock_proj = MagicMock()

    with patch.object(server.resolve, 'get_timeline', return_value=(mock_proj, mock_tl, None)):
        result = server.fx(action="apply_look", look="nonexistent_look")

    assert result["success"] is False
    assert "nonexistent_look" in result["error"]


def test_apply_look_calls_setcdl():
    from unittest.mock import MagicMock, patch
    import server

    mock_item = MagicMock()
    mock_item.SetCDL.return_value = True
    mock_tl = MagicMock()
    mock_tl.GetCurrentVideoItem.return_value = mock_item
    mock_proj = MagicMock()

    with patch.object(server.resolve, 'get_timeline', return_value=(mock_proj, mock_tl, None)):
        result = server.fx(action="apply_look", look="aerial_clean")

    assert result["success"] is True
    mock_item.SetCDL.assert_called_once()
    cdl_arg = mock_item.SetCDL.call_args[0][0]
    assert cdl_arg["NodeIndex"] == "1"
    assert cdl_arg["Saturation"] == "1.050"


def test_install_templates_creates_directory(tmp_path):
    """install_templates should create template dir and write .comp files."""
    import server
    from unittest.mock import patch, MagicMock

    # Patch _TEMPLATE_DIR to use tmp_path
    with patch.object(server, '_TEMPLATE_DIR', str(tmp_path / "transitions")):
        # Patch Fusion API — simulate successful comp generation
        mock_comp = MagicMock()
        mock_comp.Save.return_value = True
        mock_comp.AddTool.return_value = MagicMock()
        mock_fusion = MagicMock()
        mock_fusion.NewComp.return_value = mock_comp

        r = MagicMock()
        r.Fusion.return_value = mock_fusion

        with patch.object(server.resolve, 'connect', return_value=r):
            result = server.fx(action="install_templates")

    # Directory must exist
    assert (tmp_path / "transitions").exists()
    assert result["success"] is True


def test_add_transition_missing_params_returns_error():
    import server
    result = server.fx(action="add_transition", transition="glitch")
    assert result["success"] is False
    assert "track_index" in result["error"]


def test_add_transition_unknown_transition_returns_error():
    import server
    from unittest.mock import MagicMock, patch

    mock_tl = MagicMock()
    mock_proj = MagicMock()
    with patch.object(server.resolve, 'get_timeline', return_value=(mock_proj, mock_tl, None)):
        result = server.fx(action="add_transition", transition="nonexistent",
                          track_index=1, item_index=2, duration=24)
    assert result["success"] is False
    assert "nonexistent" in result["error"]


def test_add_transition_template_missing_returns_error():
    import server
    from unittest.mock import MagicMock, patch

    items = [MagicMock(), MagicMock(), MagicMock()]
    mock_tl = MagicMock()
    mock_tl.GetItemListInTrack.return_value = items
    mock_proj = MagicMock()

    with patch.object(server.resolve, 'get_timeline', return_value=(mock_proj, mock_tl, None)):
        with patch.object(server, '_TEMPLATE_DIR', '/nonexistent/path'):
            result = server.fx(action="add_transition", transition="glitch",
                              track_index=1, item_index=1, duration=24)

    assert result["success"] is False
    assert "install_templates" in result["error"]


def test_create_3d_text_missing_text_returns_error():
    import server
    from unittest.mock import MagicMock, patch
    mock_tl = MagicMock()
    mock_proj = MagicMock()
    with patch.object(server.resolve, 'get_timeline', return_value=(mock_proj, mock_tl, None)):
        result = server.fx(action="create_3d_text", clip_index=1)
    assert result["success"] is False
    assert "text" in result["error"]


def test_parse_hex_color_white():
    from server import _parse_hex_color
    r, g, b = _parse_hex_color("#FFFFFF")
    assert r == 1.0 and g == 1.0 and b == 1.0


def test_parse_hex_color_red():
    from server import _parse_hex_color
    r, g, b = _parse_hex_color("#FF0000")
    assert r == 1.0 and g == 0.0 and b == 0.0


def test_parse_hex_color_without_hash():
    from server import _parse_hex_color
    r, g, b = _parse_hex_color("00FF00")
    assert r == 0.0 and g == 1.0 and b == 0.0


def test_create_3d_text_builds_comp(monkeypatch):
    import server
    from unittest.mock import MagicMock, patch

    # Mock timeline item
    mock_item = MagicMock()
    mock_item.GetName.return_value = "Clip_001.MP4"

    mock_tl = MagicMock()
    mock_tl.GetItemListInTrack.return_value = [mock_item]
    mock_proj = MagicMock()

    # Mock Fusion comp
    mock_tool = MagicMock()
    mock_tool.FindMainInput.return_value = MagicMock()
    mock_tool.FindMainOutput.return_value = MagicMock()
    mock_tool.FindInput.return_value = MagicMock()

    mock_comp = MagicMock()
    mock_comp.AddTool.return_value = mock_tool
    mock_item.GetFusionCompByIndex.return_value = None
    mock_item.AddFusionComp.return_value = mock_comp

    with patch.object(server.resolve, 'get_timeline', return_value=(mock_proj, mock_tl, None)):
        result = server.fx(action="create_3d_text", text="SIZILIEN", clip_index=1)

    # Should have tried to add multiple Fusion nodes
    assert mock_comp.AddTool.call_count >= 5
    # Text3D node should be one of them
    tool_names = [c[0][0] for c in mock_comp.AddTool.call_args_list]
    assert "Text3D" in tool_names
    assert "CameraTracker" in tool_names
    assert "Renderer3D" in tool_names
