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
