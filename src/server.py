"""DaVinci Resolve MCP Server — Main entry point."""

import sys
import os
from typing import Any

# Ensure Resolve scripting modules are importable
pythonpath = os.environ.get("PYTHONPATH", "")
if pythonpath and pythonpath not in sys.path:
    sys.path.insert(0, pythonpath)

from mcp.server.fastmcp import FastMCP

from resolve_connection import ResolveConnection, _err, _ok, _ser

mcp = FastMCP(
    "DaVinci Resolve",
    instructions="MCP server for controlling DaVinci Resolve via its Scripting API",
)

resolve = ResolveConnection()


# ── resolve_status ──────────────────────────────────────────────────

@mcp.tool()
def resolve_status() -> dict:
    """Get DaVinci Resolve connection status, version, current project, and current page.

    Use this tool first to verify that Resolve is running and reachable.
    """
    try:
        r = resolve.connect()
        if r is None:
            return _err(
                "Could not connect to DaVinci Resolve. "
                "Is it running with External Scripting set to Local?"
            )

        pm = r.GetProjectManager()
        project = pm.GetCurrentProject() if pm else None

        return _ok(
            connected=True,
            version=r.GetVersionString() if hasattr(r, "GetVersionString") else str(r.GetVersion()),
            project=project.GetName() if project else None,
            page=r.GetCurrentPage() if hasattr(r, "GetCurrentPage") else None,
        )
    except Exception as e:
        return _err(str(e))


# ── resolve_control ─────────────────────────────────────────────────

@mcp.tool()
def resolve_control(action: str) -> dict:
    """Control DaVinci Resolve application.

    Actions:
    - "status": Get connection status, version, project, page (same as resolve_status)
    - "get_page": Get the current page name
    - "set_page": Switch to a page. Requires params: page (media|cut|edit|fusion|color|fairlight|deliver)
    - "get_version": Get Resolve version string

    Args:
        action: The action to perform
    """
    r = resolve.connect()
    if not r:
        return _err("Not connected to DaVinci Resolve")

    if action == "status":
        return resolve_status()

    elif action == "get_page":
        return _ok(page=r.GetCurrentPage())

    elif action == "set_page":
        # Will be extended to accept page param in Phase 2
        return _err("set_page requires a 'page' parameter — coming in Phase 2")

    elif action == "get_version":
        return _ok(
            version=r.GetVersionString() if hasattr(r, "GetVersionString") else str(r.GetVersion()),
            product=r.GetProductName() if hasattr(r, "GetProductName") else None,
        )

    else:
        return _err(f"Unknown action: {action}. Valid: status, get_page, set_page, get_version")


# ── project ─────────────────────────────────────────────────────────

@mcp.tool()
def project(action: str, name: str | None = None) -> dict:
    """Manage DaVinci Resolve projects.

    Actions:
    - "list": List all projects in the current database folder
    - "get_current": Get the name of the currently open project
    - "open": Open a project by name. Requires: name
    - "save": Save the current project
    - "create": Create a new project. Requires: name
    - "close": Close the current project

    Args:
        action: The action to perform
        name: Project name (required for open, create)
    """
    pm, proj, err = resolve.check()

    if action == "list":
        if not pm:
            # check() failed but we might still have a connection
            r = resolve.connect()
            if not r:
                return _err("Not connected to DaVinci Resolve")
            pm = r.GetProjectManager()
            if not pm:
                return _err("Could not get ProjectManager")
        projects = pm.GetProjectListInCurrentFolder()
        return _ok(projects=_ser(projects))

    elif action == "get_current":
        if err and not proj:
            return err
        return _ok(project=proj.GetName())

    elif action == "open":
        if not name:
            return _err("'name' is required for action 'open'")
        if not pm:
            r = resolve.connect()
            if not r:
                return _err("Not connected")
            pm = r.GetProjectManager()
        opened = pm.LoadProject(name)
        if not opened:
            return _err(f"Could not open project '{name}'")
        return _ok(project=opened.GetName())

    elif action == "save":
        if err:
            return err
        pm_obj = resolve.connect().GetProjectManager()
        result = pm_obj.SaveProject()
        return _ok(saved=result)

    elif action == "create":
        if not name:
            return _err("'name' is required for action 'create'")
        if not pm:
            r = resolve.connect()
            if not r:
                return _err("Not connected")
            pm = r.GetProjectManager()
        created = pm.CreateProject(name)
        if not created:
            return _err(f"Could not create project '{name}' — does it already exist?")
        return _ok(project=created.GetName())

    elif action == "close":
        if err:
            return err
        pm_obj = resolve.connect().GetProjectManager()
        result = pm_obj.CloseProject(proj)
        return _ok(closed=result)

    else:
        return _err(
            f"Unknown action: {action}. "
            "Valid: list, get_current, open, save, create, close"
        )


if __name__ == "__main__":
    mcp.run()
