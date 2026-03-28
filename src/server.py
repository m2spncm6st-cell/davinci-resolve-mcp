"""DaVinci Resolve MCP Server — Main entry point."""

import functools
import logging
import sys
import os
from typing import Any

# Ensure Resolve scripting modules are importable
pythonpath = os.environ.get("PYTHONPATH", "")
if pythonpath and pythonpath not in sys.path:
    sys.path.insert(0, pythonpath)

from mcp.server.fastmcp import FastMCP

from resolve_connection import ResolveConnection, _err, _ok, _ser

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "DaVinci Resolve",
    instructions="MCP server for controlling DaVinci Resolve via its Scripting API",
)

resolve = ResolveConnection()


def safe_tool(func):
    """Decorator that catches all exceptions in a tool and returns _err() instead of crashing."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("Tool '%s' crashed", func.__name__)
            return _err(f"Internal error in {func.__name__}: {e}")
    return wrapper


# ── resolve_status ──────────────────────────────────────────────────

@mcp.tool()
@safe_tool
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
@safe_tool
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
@safe_tool
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
@safe_tool
def timeline(
    action: str,
    name: str | None = None,
    index: int | None = None,
    track_type: str | None = None,
    track_index: int | None = None,
    export_format: str | None = None,
    file_path: str | None = None,
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
    - "add_marker": Add a marker. Requires: track_index (frame number). Optional: name (color, default Blue)
    - "delete_markers": Delete markers by color. Optional: name (color, default "All")
    - "get_settings": Get timeline settings (resolution, framerate, etc.)
    - "duplicate": Duplicate current timeline. Optional: name
    - "add_track": Add a track. Requires: track_type (video|audio|subtitle)
    - "delete_track": Delete a track. Requires: track_type, track_index
    - "export": Export timeline. Requires: file_path, export_format (AAF|EDL|FCPXML_1_8|FCPXML_1_9|DRT|OTIO|CSV|TAB)
    - "insert_title": Insert a title at playhead. Requires: name (title template name)
    - "insert_generator": Insert a generator at playhead. Requires: name (generator name)
    - "delete_clips": Delete all clips on a track. Requires: track_type, track_index
    - "get_marker_clips": Find clips overlapping markers. Optional: name (marker color filter)

    Args:
        action: The action to perform
        name: Timeline/title/generator name, or marker color (for get_marker_clips), or marker color to delete
        index: Timeline index, 1-based (for set_current)
        track_type: Track type: video, audio, subtitle
        track_index: Track index, 1-based; or frame number (for add_marker)
        export_format: Export format (for export action)
        file_path: File path (for export action)
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

    elif action == "add_marker":
        if err:
            return err
        if not track_index:
            return _err("'track_index' is required (frame number to place marker)")
        marker_color = name or "Blue"
        result = tl.AddMarker(track_index, marker_color, "", "", 1)
        return _ok(frame=track_index, color=marker_color, added=result)

    elif action == "delete_markers":
        if err:
            return err
        color = name or "All"
        result = tl.DeleteMarkersByColor(color)
        return _ok(color=color, deleted=result)

    elif action == "get_settings":
        if err:
            return err
        settings = {}
        for key in ("timelineFrameRate", "timelineResolutionWidth", "timelineResolutionHeight",
                     "timelineOutputResolutionWidth", "timelineOutputResolutionHeight",
                     "timelinePlaybackFrameRate", "videoBitDepth", "videoMonitorFormat"):
            val = tl.GetSetting(key)
            if val:
                settings[key] = val
        return _ok(settings=settings)

    elif action == "duplicate":
        if err:
            return err
        new_tl = tl.DuplicateTimeline(name) if name else tl.DuplicateTimeline()
        if not new_tl:
            return _err("Could not duplicate timeline")
        return _ok(timeline=new_tl.GetName())

    elif action == "add_track":
        if err:
            return err
        if not track_type:
            return _err("'track_type' is required (video|audio|subtitle)")
        result = tl.AddTrack(track_type)
        return _ok(track_type=track_type, added=result)

    elif action == "delete_track":
        if err:
            return err
        if not track_type or not track_index:
            return _err("'track_type' and 'track_index' are required")
        result = tl.DeleteTrack(track_type, track_index)
        return _ok(track_type=track_type, track_index=track_index, deleted=result)

    elif action == "export":
        if err:
            return err
        if not file_path:
            return _err("'file_path' is required")
        fmt = export_format or "FCPXML_1_9"
        fmt_map = {
            "AAF": 0, "DRT": 1, "EDL": 2, "FCP_7_XML": 3,
            "FCPXML_1_8": 7, "FCPXML_1_9": 8, "FCPXML_1_10": 9,
            "CSV": 13, "TAB": 14, "OTIO": 18,
        }
        fmt_val = fmt_map.get(fmt.upper())
        if fmt_val is None:
            return _err(f"Unknown format '{fmt}'. Valid: {', '.join(fmt_map.keys())}")
        result = tl.Export(file_path, fmt_val, 0)
        return _ok(file_path=file_path, format=fmt, exported=result)

    elif action == "insert_title":
        if err:
            return err
        if not name:
            return _err("'name' is required (title template name, e.g. 'Text+')")
        item = tl.InsertTitleIntoTimeline(name)
        if not item:
            # Try Fusion title
            item = tl.InsertFusionTitleIntoTimeline(name)
        if not item:
            return _err(f"Could not insert title '{name}'")
        return _ok(title=item.GetName(), start=item.GetStart(), end=item.GetEnd())

    elif action == "insert_generator":
        if err:
            return err
        if not name:
            return _err("'name' is required (generator name)")
        item = tl.InsertGeneratorIntoTimeline(name)
        if not item:
            return _err(f"Could not insert generator '{name}'")
        return _ok(generator=item.GetName(), start=item.GetStart(), end=item.GetEnd())

    elif action == "delete_clips":
        if err:
            return err
        if not track_type or not track_index:
            return _err("'track_type' and 'track_index' are required")
        items = tl.GetItemListInTrack(track_type, track_index)
        if not items:
            return _ok(deleted=0)
        result = tl.DeleteClips(items)
        return _ok(deleted=len(items), result=result)

    elif action == "get_marker_clips":
        if err:
            return err
        markers = tl.GetMarkers()
        if not markers:
            return _ok(clips=[], marker_count=0)
        color_filter = name  # name-Parameter als optionaler Farbfilter
        matched = []
        video_count = tl.GetTrackCount("video")
        # Collect items per track once (avoid N×M API calls)
        track_items = {}
        for track_i in range(1, video_count + 1):
            items = tl.GetItemListInTrack("video", track_i)
            track_items[track_i] = list(items) if items else []
        for frame, marker_data in markers.items():
            if color_filter and marker_data.get("color") != color_filter:
                continue
            for track_i, items in track_items.items():
                for item in items:
                    start = item.GetStart()
                    end = item.GetEnd()
                    if start <= frame < end:
                        matched.append({
                            "marker_frame": frame,
                            "marker_name": marker_data.get("name", ""),
                            "marker_color": marker_data.get("color", ""),
                            "clip_name": item.GetName(),
                            "clip_start": start,
                            "clip_end": end,
                            "track_index": track_i,
                        })
        return _ok(clips=matched, marker_count=len(markers))

    else:
        return _err(
            f"Unknown action: {action}. Valid: list, get_current, set_current, create, "
            "get_tracks, get_items, get_markers, add_marker, delete_markers, get_settings, "
            "duplicate, add_track, delete_track, export, insert_title, insert_generator, delete_clips, "
            "get_marker_clips"
        )


# ── timeline_item ───────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def timeline_item(
    action: str,
    track_type: str | None = None,
    track_index: int | None = None,
    item_index: int | None = None,
    property_name: str | None = None,
    property_value: str | None = None,
    clip_color: str | None = None,
) -> dict:
    """Edit individual clips/items on the timeline.

    This is the core editing tool — use it to change clip properties like opacity,
    zoom, position, rotation, speed, crop, etc.

    Actions:
    - "get_current": Get the current video item under the playhead
    - "get_properties": Get all editable properties of a clip. Optional: track_type, track_index, item_index
    - "set_property": Set a clip property. Requires: property_name, property_value. Optional: track_type, track_index, item_index
    - "get_info": Get detailed info about a specific clip. Requires: track_type, track_index, item_index (0-based)
    - "set_clip_color": Set clip color. Requires: clip_color (Orange, Apricot, Yellow, Lime, Olive, Green, Teal, Navy, Blue, Purple, Violet, Pink, Tan, Beige, Brown, Chocolate)
    - "clear_clip_color": Remove clip color
    - "set_enabled": Enable/disable a clip. Requires: property_value ("true"/"false")
    - "get_source_info": Get source frame range of the clip

    Available properties for set_property:
    Pan, Tilt, ZoomX, ZoomY, ZoomGang, RotationAngle, AnchorPointX, AnchorPointY,
    Pitch, Yaw, FlipX, FlipY, CropLeft, CropRight, CropTop, CropBottom, CropSoftness,
    CropRetain, Opacity, Distortion, RetimeProcess, MotionEstimation, Scaling,
    ResizeFilter, DynamicZoomEase, CompositeMode

    Args:
        action: The action to perform
        track_type: Track type (default "video")
        track_index: Track index, 1-based (default 1)
        item_index: Item index on the track, 0-based
        property_name: Property key (for set_property)
        property_value: Property value as string (for set_property, set_enabled)
        clip_color: Clip color name (for set_clip_color)
    """
    proj, tl, err = resolve.get_timeline()
    if err:
        return err

    # Helper to get target item
    def _get_item():
        if item_index is not None:
            tt = track_type or "video"
            ti = track_index or 1
            items = tl.GetItemListInTrack(tt, ti)
            if not items or item_index >= len(items):
                return None, _err(f"No item at index {item_index} on {tt} track {ti}")
            return items[item_index], None
        else:
            item = tl.GetCurrentVideoItem()
            if not item:
                return None, _err("No current video item — select one or provide item_index")
            return item, None

    if action == "get_current":
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        return _ok(
            name=item.GetName(),
            start=item.GetStart(),
            end=item.GetEnd(),
            duration=item.GetDuration(),
            enabled=item.GetClipEnabled(),
            color=item.GetClipColor() if hasattr(item, "GetClipColor") else None,
        )

    elif action == "get_properties":
        item, item_err = _get_item()
        if item_err:
            return item_err
        props = item.GetProperty()
        return _ok(item=item.GetName(), properties=_ser(props))

    elif action == "set_property":
        if not property_name:
            return _err("'property_name' is required")
        if property_value is None:
            return _err("'property_value' is required")
        item, item_err = _get_item()
        if item_err:
            return item_err
        # Convert value to appropriate type
        val = property_value
        if val.lower() in ("true", "false"):
            val = val.lower() == "true"
        else:
            try:
                val = float(val)
                if val == int(val):
                    val = int(val)
            except ValueError:
                pass
        result = item.SetProperty(property_name, val)
        return _ok(item=item.GetName(), property=property_name, value=val, set=result)

    elif action == "get_info":
        item, item_err = _get_item()
        if item_err:
            return item_err
        info = {
            "name": item.GetName(),
            "start": item.GetStart(),
            "end": item.GetEnd(),
            "duration": item.GetDuration(),
            "enabled": item.GetClipEnabled(),
            "color": item.GetClipColor() if hasattr(item, "GetClipColor") else None,
            "flags": item.GetFlagList() if hasattr(item, "GetFlagList") else [],
            "fusion_comps": item.GetFusionCompCount() if hasattr(item, "GetFusionCompCount") else 0,
        }
        # Source info
        if hasattr(item, "GetSourceStartFrame"):
            info["source_start"] = item.GetSourceStartFrame()
            info["source_end"] = item.GetSourceEndFrame()
        if hasattr(item, "GetLeftOffset"):
            info["left_offset"] = item.GetLeftOffset()
            info["right_offset"] = item.GetRightOffset()
        # MediaPool link
        mpi = item.GetMediaPoolItem()
        if mpi:
            info["media_pool_item"] = mpi.GetName()
        return _ok(**info)

    elif action == "set_clip_color":
        if not clip_color:
            return _err("'clip_color' is required")
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.SetClipColor(clip_color)
        return _ok(color=clip_color, set=result)

    elif action == "clear_clip_color":
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.ClearClipColor()
        return _ok(cleared=result)

    elif action == "set_enabled":
        if property_value is None:
            return _err("'property_value' is required ('true' or 'false')")
        item, item_err = _get_item()
        if item_err:
            return item_err
        enabled = property_value.lower() != "false"
        result = item.SetClipEnabled(enabled)
        return _ok(enabled=enabled, set=result)

    elif action == "get_source_info":
        item, item_err = _get_item()
        if item_err:
            return item_err
        info = {"name": item.GetName()}
        if hasattr(item, "GetSourceStartFrame"):
            info["source_start_frame"] = item.GetSourceStartFrame()
            info["source_end_frame"] = item.GetSourceEndFrame()
        if hasattr(item, "GetLeftOffset"):
            info["left_offset"] = item.GetLeftOffset()
            info["right_offset"] = item.GetRightOffset()
        mpi = item.GetMediaPoolItem()
        if mpi:
            info["media_pool_clip"] = mpi.GetName()
            mark = mpi.GetMarkInOut() if hasattr(mpi, "GetMarkInOut") else None
            if mark:
                info["mark_in_out"] = _ser(mark)
        return _ok(**info)

    else:
        return _err(
            f"Unknown action: {action}. Valid: get_current, get_properties, set_property, "
            "get_info, set_clip_color, clear_clip_color, set_enabled, get_source_info"
        )


# ── media_pool ──────────────────────────────────────────────────────

@mcp.tool()
@safe_tool
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
    - "delete_folder": Delete a subfolder. Requires: folder_name
    - "list_clips": List all clips in the current folder
    - "get_clip_info": Get detailed clip properties. Requires: folder_name (= clip name)
    - "import_media": Import media files. Requires: file_paths (list of absolute paths)
    - "create_timeline_from_clips": Create timeline from all clips in current folder. Requires: timeline_name
    - "get_root_folder": Navigate to root folder
    - "selected_clips": Get currently selected clips in the Media Pool
    - "append_to_timeline": Append clips from current folder to active timeline. Optional: file_paths (clip names to filter)

    Args:
        action: The action to perform
        folder_name: Folder name (for set/create/delete_folder) or clip name (for get_clip_info)
        file_paths: List of absolute file paths (for import_media) or clip names (for append_to_timeline)
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

    elif action == "get_clip_info":
        if err:
            return err
        if not folder_name:
            return _err("'folder_name' is required (clip name to inspect)")
        current = mp.GetCurrentFolder()
        clips = current.GetClipList() if current else []
        for clip in (clips or []):
            if clip.GetName() == folder_name:
                props = clip.GetClipProperty() or {}
                metadata = clip.GetMetadata() or {}
                return _ok(
                    name=clip.GetName(),
                    properties=_ser(props),
                    metadata=_ser(metadata),
                    media_id=clip.GetMediaId() if hasattr(clip, "GetMediaId") else None,
                    unique_id=clip.GetUniqueId() if hasattr(clip, "GetUniqueId") else None,
                )
        return _err(f"Clip '{folder_name}' not found in current folder")

    elif action == "delete_folder":
        if err:
            return err
        if not folder_name:
            return _err("'folder_name' is required")
        current = mp.GetCurrentFolder()
        subfolders = current.GetSubFolderList() if current else []
        for f in (subfolders or []):
            if f.GetName() == folder_name:
                result = mp.DeleteFolders([f])
                return _ok(folder=folder_name, deleted=result)
        return _err(f"Folder '{folder_name}' not found")

    elif action == "append_to_timeline":
        if err:
            return err
        # Append clips from current folder to the current timeline
        current = mp.GetCurrentFolder()
        clips = current.GetClipList() if current else []
        if not clips:
            return _err("No clips in the current folder")
        # If file_paths is given, use it as clip name filter
        if file_paths:
            selected = [c for c in clips if c.GetName() in file_paths]
            if not selected:
                return _err(f"No matching clips found. Available: {[c.GetName() for c in clips]}")
        else:
            selected = clips
        # AppendToTimeline returns a list of TimelineItems or empty list on failure
        result = mp.AppendToTimeline(selected)
        if result is None or (isinstance(result, list) and len(result) == 0):
            return _err("AppendToTimeline failed — check if a timeline is active")
        appended = result if isinstance(result, list) else [result]
        return _ok(
            appended=len(appended),
            clip_names=[c.GetName() for c in selected],
        )

    else:
        return _err(
            f"Unknown action: {action}. Valid: list_folders, get_current_folder, set_current_folder, "
            "create_folder, delete_folder, list_clips, get_clip_info, import_media, "
            "create_timeline_from_clips, get_root_folder, selected_clips, append_to_timeline"
        )


# ── color ───────────────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def color(
    action: str,
    node_index: int | None = None,
    lut_path: str | None = None,
    item_index: int | None = None,
) -> dict:
    """Color grading tools for DaVinci Resolve.

    Works on the current timeline or a specific timeline item.

    Actions:
    - "get_current_item": Get info about the current video item on the color page
    - "get_node_graph": Get the node graph of the current item (or timeline). Optional: item_index
    - "get_nodes": List all nodes and their labels in the current item's graph
    - "get_lut": Get the LUT applied to a node. Requires: node_index (1-based)
    - "set_lut": Apply a LUT to a node. Requires: node_index (1-based), lut_path
    - "set_node_enabled": Enable/disable a node. Requires: node_index. Optional: lut_path ("true"/"false", default "true")
    - "reset_grades": Reset all grades on the current item
    - "get_color_groups": List all color groups in the project
    - "get_timeline_nodes": Get the timeline-level node graph

    Args:
        action: The action to perform
        node_index: Node index, 1-based (for get_lut, set_lut, set_node_enabled)
        lut_path: Path to LUT file (for set_lut), or "true"/"false" (for set_node_enabled)
        item_index: Specific timeline item index on video track 1 (for get_node_graph)
    """
    proj, tl, err = resolve.get_timeline()

    if action == "get_current_item":
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item. Switch to the Color page and select a clip.")
        return _ok(
            name=item.GetName(),
            start=item.GetStart(),
            end=item.GetEnd(),
            duration=item.GetDuration(),
            enabled=item.GetClipEnabled() if hasattr(item, "GetClipEnabled") else None,
            color=item.GetClipColor() if hasattr(item, "GetClipColor") else None,
        )

    elif action == "get_node_graph" or action == "get_nodes":
        if err:
            return err
        # Get item to work on
        if item_index is not None:
            items = tl.GetItemListInTrack("video", 1)
            if not items or item_index < 0 or item_index >= len(items):
                return _err(f"No item at index {item_index}")
            item = items[item_index]
        else:
            item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No video item available")

        graph = item.GetNodeGraph()
        if not graph:
            return _err("Could not get node graph")

        num_nodes = graph.GetNumNodes()
        nodes = []
        for i in range(1, num_nodes + 1):
            node_info = {"index": i, "label": graph.GetNodeLabel(i)}
            lut = graph.GetLUT(i)
            if lut:
                node_info["lut"] = lut
            tools = graph.GetToolsInNode(i) if hasattr(graph, "GetToolsInNode") else None
            if tools:
                node_info["tools"] = _ser(tools)
            nodes.append(node_info)
        return _ok(item=item.GetName(), num_nodes=num_nodes, nodes=nodes)

    elif action == "get_lut":
        if err:
            return err
        if not node_index:
            return _err("'node_index' is required (1-based)")
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        graph = item.GetNodeGraph()
        if not graph:
            return _err("Could not get node graph")
        lut = graph.GetLUT(node_index)
        return _ok(node_index=node_index, lut=lut if lut else None)

    elif action == "set_lut":
        if err:
            return err
        if not node_index or not lut_path:
            return _err("'node_index' and 'lut_path' are required")
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        graph = item.GetNodeGraph()
        if not graph:
            return _err("Could not get node graph")
        result = graph.SetLUT(node_index, lut_path)
        return _ok(node_index=node_index, lut_path=lut_path, applied=result)

    elif action == "set_node_enabled":
        if err:
            return err
        if not node_index:
            return _err("'node_index' is required (1-based)")
        enabled = lut_path != "false" if lut_path else True
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        graph = item.GetNodeGraph()
        if not graph:
            return _err("Could not get node graph")
        result = graph.SetNodeEnabled(node_index, enabled)
        return _ok(node_index=node_index, enabled=enabled, result=result)

    elif action == "reset_grades":
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        graph = item.GetNodeGraph()
        if not graph:
            return _err("Could not get node graph")
        result = graph.ResetAllGrades()
        return _ok(reset=result)

    elif action == "get_color_groups":
        pm, proj2, err2 = resolve.check()
        if err2:
            return err2
        groups = proj2.GetColorGroupsList()
        if not groups:
            return _ok(groups=[])
        return _ok(groups=[{"name": g.GetName()} for g in groups])

    elif action == "get_timeline_nodes":
        if err:
            return err
        graph = tl.GetNodeGraph()
        if not graph:
            return _err("Could not get timeline node graph")
        num_nodes = graph.GetNumNodes()
        nodes = []
        for i in range(1, num_nodes + 1):
            nodes.append({"index": i, "label": graph.GetNodeLabel(i)})
        return _ok(num_nodes=num_nodes, nodes=nodes)

    else:
        return _err(
            f"Unknown action: {action}. Valid: get_current_item, get_node_graph, get_nodes, "
            "get_lut, set_lut, set_node_enabled, reset_grades, get_color_groups, get_timeline_nodes"
        )


# ── deliver ─────────────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def deliver(
    action: str,
    preset_name: str | None = None,
    target_dir: str | None = None,
    file_name: str | None = None,
    render_format: str | None = None,
    render_codec: str | None = None,
    job_id: str | None = None,
) -> dict:
    """Manage rendering and delivery in DaVinci Resolve.

    Actions:
    - "get_formats": List available render formats
    - "get_codecs": List codecs for a format. Requires: render_format
    - "get_presets": List available render presets
    - "load_preset": Load a render preset. Requires: preset_name
    - "get_current_format": Get current render format and codec
    - "set_format": Set render format and codec. Requires: render_format, render_codec
    - "set_render_settings": Configure render output. Optional: target_dir, file_name
    - "add_job": Add current timeline to the render queue
    - "list_jobs": List all render jobs
    - "get_job_status": Get status of a render job. Requires: job_id
    - "start_render": Start rendering all queued jobs (or specific job_id)
    - "stop_render": Stop current render
    - "is_rendering": Check if rendering is in progress
    - "delete_all_jobs": Clear the render queue

    Args:
        action: The action to perform
        preset_name: Render preset name
        target_dir: Output directory path
        file_name: Output file name (without extension)
        render_format: Render format (e.g. "mp4", "mov")
        render_codec: Render codec (e.g. "H.265", "H.264")
        job_id: Render job ID
    """
    pm, proj, err = resolve.check()

    if action == "get_formats":
        if err:
            return err
        formats = proj.GetRenderFormats()
        return _ok(formats=_ser(formats))

    elif action == "get_codecs":
        if err:
            return err
        if not render_format:
            return _err("'render_format' is required")
        codecs = proj.GetRenderCodecs(render_format)
        return _ok(format=render_format, codecs=_ser(codecs))

    elif action == "get_presets":
        if err:
            return err
        presets = proj.GetPresetList()
        return _ok(presets=_ser(presets))

    elif action == "load_preset":
        if err:
            return err
        if not preset_name:
            return _err("'preset_name' is required")
        result = proj.LoadRenderPreset(preset_name)
        return _ok(preset=preset_name, loaded=result)

    elif action == "get_current_format":
        if err:
            return err
        fmt = proj.GetCurrentRenderFormatAndCodec()
        return _ok(format_and_codec=_ser(fmt))

    elif action == "set_format":
        if err:
            return err
        if not render_format or not render_codec:
            return _err("'render_format' and 'render_codec' are required")
        result = proj.SetCurrentRenderFormatAndCodec(render_format, render_codec)
        return _ok(format=render_format, codec=render_codec, set=result)

    elif action == "set_render_settings":
        if err:
            return err
        settings = {}
        if target_dir:
            settings["TargetDir"] = target_dir
        if file_name:
            settings["CustomName"] = file_name
        if not settings:
            return _err("Provide at least 'target_dir' or 'file_name'")
        result = proj.SetRenderSettings(settings)
        return _ok(settings=settings, applied=result)

    elif action == "add_job":
        if err:
            return err
        job = proj.AddRenderJob()
        if not job:
            return _err("Could not add render job. Check render settings and timeline.")
        return _ok(job_id=job)

    elif action == "list_jobs":
        if err:
            return err
        jobs = proj.GetRenderJobList()
        return _ok(jobs=_ser(jobs))

    elif action == "get_job_status":
        if err:
            return err
        if not job_id:
            return _err("'job_id' is required")
        status = proj.GetRenderJobStatus(job_id)
        return _ok(job_id=job_id, status=_ser(status))

    elif action == "start_render":
        if err:
            return err
        if job_id:
            result = proj.StartRendering(job_id)
        else:
            result = proj.StartRendering()
        return _ok(started=result)

    elif action == "stop_render":
        if err:
            return err
        proj.StopRendering()
        return _ok(stopped=True)

    elif action == "is_rendering":
        if err:
            return err
        return _ok(rendering=proj.IsRenderingInProgress())

    elif action == "delete_all_jobs":
        if err:
            return err
        result = proj.DeleteAllRenderJobs()
        return _ok(deleted=result)

    else:
        return _err(
            f"Unknown action: {action}. Valid: get_formats, get_codecs, get_presets, load_preset, "
            "get_current_format, set_format, set_render_settings, add_job, list_jobs, "
            "get_job_status, start_render, stop_render, is_rendering, delete_all_jobs"
        )


# ── fusion ──────────────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def fusion(
    action: str,
    comp_name: str | None = None,
    comp_index: int | None = None,
    file_path: str | None = None,
    new_name: str | None = None,
) -> dict:
    """Manage Fusion compositions on timeline items in DaVinci Resolve.

    Works on the current video item in the timeline.

    Actions:
    - "list_comps": List Fusion compositions on the current item
    - "get_comp": Get a specific composition. Optional: comp_name or comp_index (1-based)
    - "add_comp": Add a new Fusion composition to the current item
    - "import_comp": Import a Fusion composition from file. Requires: file_path
    - "export_comp": Export a composition. Requires: file_path, comp_index (1-based)
    - "delete_comp": Delete a composition by name. Requires: comp_name
    - "rename_comp": Rename a composition. Requires: comp_name, new_name
    - "insert_fusion_clip": Insert a Fusion clip into the timeline at the playhead

    Args:
        action: The action to perform
        comp_name: Composition name (for get_comp, delete_comp, rename_comp)
        comp_index: Composition index, 1-based (for get_comp, export_comp)
        file_path: File path (for import_comp, export_comp)
        new_name: New name (for rename_comp)
    """
    proj, tl, err = resolve.get_timeline()

    if action == "insert_fusion_clip":
        if err:
            return err
        item = tl.InsertFusionCompositionIntoTimeline()
        if not item:
            return _err("Could not insert Fusion composition into timeline")
        return _ok(item=item.GetName())

    # All other actions need the current video item
    if err:
        return err
    item = tl.GetCurrentVideoItem()
    if not item:
        return _err("No current video item. Select a clip first.")

    if action == "list_comps":
        count = item.GetFusionCompCount()
        names = item.GetFusionCompNameList()
        return _ok(count=count, compositions=_ser(names))

    elif action == "get_comp":
        if comp_name:
            comp = item.GetFusionCompByName(comp_name)
        elif comp_index:
            comp = item.GetFusionCompByIndex(comp_index)
        else:
            return _err("Provide 'comp_name' or 'comp_index'")
        if not comp:
            return _err("Composition not found")
        return _ok(composition=str(comp))

    elif action == "add_comp":
        comp = item.AddFusionComp()
        if not comp:
            return _err("Could not add Fusion composition")
        return _ok(added=True, count=item.GetFusionCompCount())

    elif action == "import_comp":
        if not file_path:
            return _err("'file_path' is required")
        comp = item.ImportFusionComp(file_path)
        if not comp:
            return _err(f"Could not import Fusion comp from '{file_path}'")
        return _ok(imported=True)

    elif action == "export_comp":
        if not file_path or not comp_index:
            return _err("'file_path' and 'comp_index' are required")
        result = item.ExportFusionComp(file_path, comp_index)
        return _ok(exported=result, path=file_path)

    elif action == "delete_comp":
        if not comp_name:
            return _err("'comp_name' is required")
        result = item.DeleteFusionCompByName(comp_name)
        return _ok(deleted=result)

    elif action == "rename_comp":
        if not comp_name or not new_name:
            return _err("'comp_name' and 'new_name' are required")
        result = item.RenameFusionCompByName(comp_name, new_name)
        return _ok(renamed=result, old_name=comp_name, new_name=new_name)

    else:
        return _err(
            f"Unknown action: {action}. Valid: list_comps, get_comp, add_comp, "
            "import_comp, export_comp, delete_comp, rename_comp, insert_fusion_clip"
        )


# ── transition ──────────────────────────────────────────────────────

TRANSITION_TYPES = ["Cut", "Dissolve", "DipToColor", "Wipe"]


@mcp.tool()
@safe_tool
def transition(
    action: str,
    track_type: str | None = None,
    track_index: int | None = None,
    item_index: int | None = None,
    transition_type: str | None = None,
    duration: int | None = None,
) -> dict:
    """Add, remove, or inspect transitions between clips in DaVinci Resolve.

    Actions:
    - "list_types": List available transition types (Cut, Dissolve, DipToColor, Wipe)
    - "get": Get the transition on a clip. Requires: track_type, track_index, item_index
    - "add": Add a transition after a clip. Requires: track_type, track_index, item_index,
             transition_type, duration (frames). Applies between clip[item_index] and clip[item_index+1].
    - "remove": Remove transition from a clip. Requires: track_type, track_index, item_index

    Args:
        action: The action to perform
        track_type: Track type ("video" or "audio")
        track_index: Track index, 1-based
        item_index: Clip index within the track, 1-based
        transition_type: One of: Cut, Dissolve, DipToColor, Wipe
        duration: Transition duration in frames
    """
    if action == "list_types":
        return _ok(types=TRANSITION_TYPES)

    proj, tl, err = resolve.get_timeline()
    if err:
        return err

    if not track_type or track_index is None or item_index is None:
        return _err("'track_type', 'track_index', and 'item_index' are required (1-based)")

    items = tl.GetItemListInTrack(track_type, track_index)
    if items is None:
        return _err(f"Could not get items from {track_type} track {track_index}")
    items = list(items)
    if item_index < 1 or item_index > len(items):
        return _err(f"item_index {item_index} out of range (1–{len(items)})")
    item = items[item_index - 1]

    if action == "get":
        if not hasattr(item, "GetTransition"):
            return _err("GetTransition() not available in this Resolve version")
        trans = item.GetTransition()
        return _ok(track_type=track_type, track_index=track_index, item_index=item_index, transition=_ser(trans))

    elif action == "add":
        if not transition_type:
            return _err(f"'transition_type' is required. Valid: {', '.join(TRANSITION_TYPES)}")
        if transition_type not in TRANSITION_TYPES:
            return _err(f"Unknown transition_type '{transition_type}'. Valid: {', '.join(TRANSITION_TYPES)}")
        if duration is None:
            return _err("'duration' is required (frames as int, e.g. 24 for 1 second at 24fps)")
        if not hasattr(item, "AddTransition"):
            return _err("AddTransition() not available in this Resolve version")
        result = item.AddTransition(transition_type, duration)
        return _ok(
            track_type=track_type, track_index=track_index, item_index=item_index,
            transition_type=transition_type, duration=duration, added=result
        )

    elif action == "remove":
        if not hasattr(item, "DeleteTransition"):
            return _err("DeleteTransition() not available in this Resolve version")
        result = item.DeleteTransition()
        return _ok(track_type=track_type, track_index=track_index, item_index=item_index, removed=result)

    else:
        return _err(
            f"Unknown action: {action}. Valid: list_types, get, add, remove"
        )


# ── fairlight ───────────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def fairlight(
    action: str,
    track_index: int | None = None,
    item_index: int | None = None,
    volume: float | None = None,
    muted: bool | None = None,
    pan: float | None = None,
    duration: int | None = None,
) -> dict:
    """Audio/Fairlight tools for DaVinci Resolve.

    Actions:
    - "get_audio_tracks": List all audio tracks with details
    - "get_audio_items": Get audio items in a track. Requires: track_index (1-based)
    - "get_volume": Get clip volume. Requires: track_index, item_index (1-based)
    - "set_volume": Set clip volume in dB. Requires: track_index, item_index, volume (float)
    - "set_mute": Mute or unmute a track. Requires: track_index, muted (bool)
    - "set_pan": Set clip pan. Requires: track_index, item_index, pan (-1.0 to 1.0)
    - "fade_in": Set fade-in on clip. Requires: track_index, item_index, duration (frames)
    - "fade_out": Set fade-out on clip. Requires: track_index, item_index, duration (frames)

    Args:
        action: The action to perform
        track_index: Audio track index, 1-based
        item_index: Clip index within the track, 1-based
        volume: Volume in dB (e.g. -6.0)
        muted: True to mute, False to unmute
        pan: Pan position (-1.0 = full left, 0.0 = center, 1.0 = full right)
        duration: Fade duration in frames
    """
    proj, tl, err = resolve.get_timeline()
    if err:
        return err

    if action == "get_audio_tracks":
        count = tl.GetTrackCount("audio")
        tracks = []
        for i in range(1, count + 1):
            track_info = {
                "index": i,
                "name": tl.GetTrackName("audio", i),
                "enabled": tl.GetIsTrackEnabled("audio", i) if hasattr(tl, "GetIsTrackEnabled") else None,
                "locked": tl.GetIsTrackLocked("audio", i) if hasattr(tl, "GetIsTrackLocked") else None,
            }
            tracks.append(track_info)
        return _ok(count=count, tracks=tracks)

    elif action == "get_audio_items":
        if track_index is None:
            return _err("'track_index' is required (1-based)")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        result = []
        for item in items:
            result.append({
                "name": item.GetName(),
                "start": item.GetStart(),
                "end": item.GetEnd(),
                "duration": item.GetDuration(),
            })
        return _ok(track_index=track_index, items=result)

    elif action == "get_volume":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        if not hasattr(item, "GetVolume"):
            return _err("GetVolume() not available in this Resolve version")
        vol = item.GetVolume()
        return _ok(track_index=track_index, item_index=item_index, volume=vol)

    elif action == "set_volume":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        if volume is None:
            return _err("'volume' is required (dB as float, e.g. -6.0)")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        if not hasattr(item, "SetVolume"):
            return _err("SetVolume() not available in this Resolve version")
        result = item.SetVolume(volume)
        return _ok(track_index=track_index, item_index=item_index, volume=volume, set=result)

    elif action == "set_mute":
        if track_index is None:
            return _err("'track_index' is required (1-based)")
        if muted is None:
            return _err("'muted' is required (true to mute, false to unmute)")
        if not hasattr(tl, "SetTrackEnabled"):
            return _err("SetTrackEnabled() not available in this Resolve version")
        result = tl.SetTrackEnabled("audio", track_index, not muted)
        return _ok(track_index=track_index, muted=muted, set=result)

    elif action == "set_pan":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        if pan is None:
            return _err("'pan' is required (-1.0 = full left, 0.0 = center, 1.0 = full right)")
        if not -1.0 <= pan <= 1.0:
            return _err("'pan' must be between -1.0 and 1.0")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        if not hasattr(item, "SetProperty"):
            return _err("SetProperty() not available in this Resolve version")
        result = item.SetProperty("Pan", pan)
        return _ok(track_index=track_index, item_index=item_index, pan=pan, set=result)

    elif action == "fade_in":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        if duration is None:
            return _err("'duration' is required (frames as int, e.g. 24 for 1 second at 24fps)")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        if not hasattr(item, "SetProperty"):
            return _err("SetProperty() not available in this Resolve version")
        result = item.SetProperty("FadeInDuration", duration)
        return _ok(track_index=track_index, item_index=item_index, duration=duration, set=result)

    elif action == "fade_out":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        if duration is None:
            return _err("'duration' is required (frames as int, e.g. 24 for 1 second at 24fps)")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        if not hasattr(item, "SetProperty"):
            return _err("SetProperty() not available in this Resolve version")
        result = item.SetProperty("FadeOutDuration", duration)
        return _ok(track_index=track_index, item_index=item_index, duration=duration, set=result)

    else:
        return _err(
            f"Unknown action: {action}. Valid: get_audio_tracks, get_audio_items, "
            "get_volume, set_volume, set_mute, set_pan, fade_in, fade_out"
        )


if __name__ == "__main__":
    mcp.run()
