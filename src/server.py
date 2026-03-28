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
def resolve_control(action: str, page: str | None = None) -> dict:
    """Control DaVinci Resolve application.

    Actions:
    - "status": Get connection status, version, project, page
    - "get_page": Get the current page name
    - "set_page": Switch to a page. Requires: page (media|cut|edit|fusion|color|fairlight|deliver)
    - "get_version": Get Resolve version string

    Args:
        action: The action to perform
        page: Target page for set_page action
    """
    r = resolve.connect()
    if not r:
        return _err("Not connected to DaVinci Resolve")

    if action == "status":
        return resolve_status()

    elif action == "get_page":
        return _ok(page=r.GetCurrentPage())

    elif action == "set_page":
        if not page:
            return _err("'page' is required. Valid: media, cut, edit, fusion, color, fairlight, deliver")
        valid_pages = ("media", "cut", "edit", "fusion", "color", "fairlight", "deliver")
        if page not in valid_pages:
            return _err(f"Invalid page '{page}'. Valid: {', '.join(valid_pages)}")
        result = r.OpenPage(page)
        return _ok(page=page, switched=result)

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


# ── timeline ────────────────────────────────────────────────────────

@mcp.tool()
def timeline(
    action: str,
    name: str | None = None,
    index: int | None = None,
    track_type: str | None = None,
    track_index: int | None = None,
) -> dict:
    """Manage DaVinci Resolve timelines.

    Actions:
    - "list": List all timelines in the current project
    - "get_current": Get the current timeline name and details
    - "set_current": Set current timeline by index (1-based). Requires: index
    - "create": Create a new empty timeline. Requires: name
    - "get_tracks": Get track count and info. Optional: track_type (video|audio|subtitle)
    - "get_items": Get items in a track. Requires: track_type, track_index (1-based)
    - "get_markers": Get all markers on the current timeline
    - "duplicate": Duplicate current timeline. Optional: name

    Args:
        action: The action to perform
        name: Timeline name (for create, duplicate)
        index: Timeline index, 1-based (for set_current)
        track_type: Track type: video, audio, subtitle (for get_tracks, get_items)
        track_index: Track index, 1-based (for get_items)
    """
    proj, tl, err = resolve.get_timeline()

    if action == "list":
        pm, proj2, err2 = resolve.check()
        if err2:
            return err2
        count = proj2.GetTimelineCount()
        timelines = []
        for i in range(1, count + 1):
            t = proj2.GetTimelineByIndex(i)
            if t:
                timelines.append({"index": i, "name": t.GetName()})
        return _ok(count=count, timelines=timelines)

    elif action == "get_current":
        if err:
            return err
        return _ok(
            name=tl.GetName(),
            start_frame=tl.GetStartFrame(),
            end_frame=tl.GetEndFrame(),
            start_timecode=tl.GetStartTimecode() if hasattr(tl, "GetStartTimecode") else None,
            current_timecode=tl.GetCurrentTimecode() if hasattr(tl, "GetCurrentTimecode") else None,
            video_tracks=tl.GetTrackCount("video"),
            audio_tracks=tl.GetTrackCount("audio"),
            subtitle_tracks=tl.GetTrackCount("subtitle"),
        )

    elif action == "set_current":
        if not index:
            return _err("'index' is required (1-based)")
        pm, proj2, err2 = resolve.check()
        if err2:
            return err2
        t = proj2.GetTimelineByIndex(index)
        if not t:
            return _err(f"No timeline at index {index}")
        result = proj2.SetCurrentTimeline(t)
        return _ok(timeline=t.GetName(), switched=result)

    elif action == "create":
        if not name:
            return _err("'name' is required for action 'create'")
        pm, proj2, err2 = resolve.check()
        if err2:
            return err2
        mp = proj2.GetMediaPool()
        if not mp:
            return _err("Could not access MediaPool")
        new_tl = mp.CreateEmptyTimeline(name)
        if not new_tl:
            return _err(f"Could not create timeline '{name}'")
        return _ok(timeline=new_tl.GetName())

    elif action == "get_tracks":
        if err:
            return err
        tracks = {}
        for tt in ("video", "audio", "subtitle"):
            if track_type and tt != track_type:
                continue
            count = tl.GetTrackCount(tt)
            track_list = []
            for i in range(1, count + 1):
                track_info = {"index": i, "name": tl.GetTrackName(tt, i)}
                if hasattr(tl, "GetIsTrackEnabled"):
                    track_info["enabled"] = tl.GetIsTrackEnabled(tt, i)
                if hasattr(tl, "GetIsTrackLocked"):
                    track_info["locked"] = tl.GetIsTrackLocked(tt, i)
                track_list.append(track_info)
            tracks[tt] = {"count": count, "tracks": track_list}
        return _ok(**tracks)

    elif action == "get_items":
        if err:
            return err
        if not track_type or not track_index:
            return _err("'track_type' and 'track_index' are required")
        items = tl.GetItemListInTrack(track_type, track_index)
        if items is None:
            return _err(f"Could not get items from {track_type} track {track_index}")
        result = []
        for item in items:
            result.append({
                "name": item.GetName(),
                "start": item.GetStart(),
                "end": item.GetEnd(),
                "duration": item.GetDuration(),
            })
        return _ok(track_type=track_type, track_index=track_index, items=result)

    elif action == "get_markers":
        if err:
            return err
        markers = tl.GetMarkers()
        return _ok(markers=_ser(markers))

    elif action == "duplicate":
        if err:
            return err
        new_tl = tl.DuplicateTimeline(name) if name else tl.DuplicateTimeline()
        if not new_tl:
            return _err("Could not duplicate timeline")
        return _ok(timeline=new_tl.GetName())

    else:
        return _err(
            f"Unknown action: {action}. "
            "Valid: list, get_current, set_current, create, get_tracks, get_items, get_markers, duplicate"
        )


# ── media_pool ──────────────────────────────────────────────────────

@mcp.tool()
def media_pool(
    action: str,
    folder_name: str | None = None,
    file_paths: list[str] | None = None,
    timeline_name: str | None = None,
) -> dict:
    """Manage the DaVinci Resolve Media Pool.

    Actions:
    - "list_folders": List subfolders in the current Media Pool folder
    - "get_current_folder": Get the name of the current folder
    - "set_current_folder": Set current folder by name. Requires: folder_name
    - "create_folder": Create a subfolder. Requires: folder_name
    - "list_clips": List all clips in the current folder
    - "import_media": Import media files. Requires: file_paths (list of absolute paths)
    - "create_timeline_from_clips": Create timeline from all clips in current folder. Requires: timeline_name
    - "get_root_folder": Navigate to root folder
    - "selected_clips": Get currently selected clips in the Media Pool

    Args:
        action: The action to perform
        folder_name: Folder name (for set_current_folder, create_folder)
        file_paths: List of absolute file paths (for import_media)
        timeline_name: Name for new timeline (for create_timeline_from_clips)
    """
    proj, mp, err = resolve.get_media_pool()

    if action == "list_folders":
        if err:
            return err
        current = mp.GetCurrentFolder()
        if not current:
            return _err("Could not get current folder")
        subfolders = current.GetSubFolderList()
        return _ok(
            current_folder=current.GetName(),
            subfolders=[f.GetName() for f in subfolders] if subfolders else [],
        )

    elif action == "get_current_folder":
        if err:
            return err
        current = mp.GetCurrentFolder()
        if not current:
            return _err("Could not get current folder")
        clips = current.GetClipList()
        return _ok(
            name=current.GetName(),
            clip_count=len(clips) if clips else 0,
        )

    elif action == "set_current_folder":
        if err:
            return err
        if not folder_name:
            return _err("'folder_name' is required")
        current = mp.GetCurrentFolder()
        subfolders = current.GetSubFolderList() if current else []
        for f in (subfolders or []):
            if f.GetName() == folder_name:
                result = mp.SetCurrentFolder(f)
                return _ok(folder=folder_name, switched=result)
        return _err(f"Folder '{folder_name}' not found in current folder")

    elif action == "create_folder":
        if err:
            return err
        if not folder_name:
            return _err("'folder_name' is required")
        current = mp.GetCurrentFolder()
        new_folder = mp.AddSubFolder(current, folder_name)
        if not new_folder:
            return _err(f"Could not create folder '{folder_name}'")
        return _ok(folder=new_folder.GetName())

    elif action == "list_clips":
        if err:
            return err
        current = mp.GetCurrentFolder()
        if not current:
            return _err("Could not get current folder")
        clips = current.GetClipList()
        result = []
        for clip in (clips or []):
            clip_info = {"name": clip.GetName()}
            props = clip.GetClipProperty()
            if props and isinstance(props, dict):
                for key in ("Duration", "FPS", "Resolution", "Codec", "Type"):
                    if key in props:
                        clip_info[key.lower()] = props[key]
            result.append(clip_info)
        return _ok(folder=current.GetName(), clips=result)

    elif action == "import_media":
        if err:
            return err
        if not file_paths:
            return _err("'file_paths' is required (list of absolute paths)")
        imported = mp.ImportMedia(file_paths)
        if not imported:
            return _err("Import failed. Check that paths are valid and accessible.")
        return _ok(imported=[item.GetName() for item in imported])

    elif action == "create_timeline_from_clips":
        if err:
            return err
        if not timeline_name:
            return _err("'timeline_name' is required")
        current = mp.GetCurrentFolder()
        clips = current.GetClipList() if current else None
        if not clips:
            return _err("No clips in current folder")
        new_tl = mp.CreateTimelineFromClips(timeline_name, clips)
        if not new_tl:
            return _err(f"Could not create timeline '{timeline_name}'")
        return _ok(timeline=new_tl.GetName(), clip_count=len(clips))

    elif action == "get_root_folder":
        if err:
            return err
        root = mp.GetRootFolder()
        if not root:
            return _err("Could not get root folder")
        mp.SetCurrentFolder(root)
        return _ok(folder=root.GetName())

    elif action == "selected_clips":
        if err:
            return err
        selected = mp.GetSelectedClips()
        if not selected:
            return _ok(clips=[])
        return _ok(clips=[clip.GetName() for clip in selected])

    else:
        return _err(
            f"Unknown action: {action}. "
            "Valid: list_folders, get_current_folder, set_current_folder, create_folder, "
            "list_clips, import_media, create_timeline_from_clips, get_root_folder, selected_clips"
        )


if __name__ == "__main__":
    mcp.run()
