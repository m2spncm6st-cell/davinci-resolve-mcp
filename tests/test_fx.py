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
