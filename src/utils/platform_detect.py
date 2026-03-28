"""macOS-specific path detection for DaVinci Resolve."""

import os
import platform


def get_resolve_paths() -> dict:
    """Return platform-specific paths for DaVinci Resolve scripting."""
    if platform.system() != "Darwin":
        raise RuntimeError("Only macOS is currently supported")

    return {
        "script_api": os.environ.get(
            "RESOLVE_SCRIPT_API",
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting",
        ),
        "script_lib": os.environ.get(
            "RESOLVE_SCRIPT_LIB",
            "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so",
        ),
        "modules": os.environ.get(
            "PYTHONPATH",
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
        ),
    }
