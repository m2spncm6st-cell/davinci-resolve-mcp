#!/usr/bin/env python3
"""Quick test: is DaVinci Resolve reachable via scripting API?"""

import sys
import os

sys.path.insert(
    0,
    os.environ.get(
        "PYTHONPATH",
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
    ),
)

try:
    import DaVinciResolveScript as dvr

    resolve = dvr.scriptapp("Resolve")
    if resolve:
        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject() if pm else None
        print(f"Connected to DaVinci Resolve")
        print(f"  Project: {project.GetName() if project else 'None'}")
    else:
        print("Resolve is not reachable. Is it running with External Scripting = Local?")
        sys.exit(1)
except ImportError as e:
    print(f"Cannot import DaVinciResolveScript: {e}")
    print("Check PYTHONPATH and Python version (need 3.10-3.12)")
    sys.exit(1)
