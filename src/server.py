"""DaVinci Resolve MCP Server — Main entry point."""

import sys
import os

# Ensure Resolve scripting modules are importable
pythonpath = os.environ.get("PYTHONPATH", "")
if pythonpath and pythonpath not in sys.path:
    sys.path.insert(0, pythonpath)

from mcp.server.fastmcp import FastMCP

from resolve_connection import ResolveConnection

mcp = FastMCP(
    "DaVinci Resolve",
    description="MCP server for controlling DaVinci Resolve via its Scripting API",
)

resolve = ResolveConnection()


@mcp.tool()
def resolve_status() -> dict:
    """Get DaVinci Resolve connection status, version, current project, and current page.

    Returns a dict with:
    - connected: bool
    - version: str or None
    - project: str or None
    - page: str or None
    - error: str or None (if connection failed)
    """
    try:
        r = resolve.connect()
        if r is None:
            return {
                "connected": False,
                "version": None,
                "project": None,
                "page": None,
                "error": "Could not connect to DaVinci Resolve. Is it running with External Scripting set to Local?",
            }

        project_manager = r.GetProjectManager()
        current_project = project_manager.GetCurrentProject() if project_manager else None

        return {
            "connected": True,
            "version": r.GetVersionString() if hasattr(r, "GetVersionString") else r.GetVersion(),
            "project": current_project.GetName() if current_project else None,
            "page": r.GetCurrentPage() if hasattr(r, "GetCurrentPage") else None,
            "error": None,
        }
    except Exception as e:
        return {
            "connected": False,
            "version": None,
            "project": None,
            "page": None,
            "error": str(e),
        }


if __name__ == "__main__":
    mcp.run()
