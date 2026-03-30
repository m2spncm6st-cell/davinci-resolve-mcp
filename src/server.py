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

from resolve_connection import ResolveConnection, _err, _ok, _ser, tc_to_frames, find_lut

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
def project(action: str, name: str | None = None, settings: dict | None = None) -> dict:
    """Manage DaVinci Resolve projects.

    Actions:
    - "list": List all projects in the current database folder
    - "get_current": Get the name of the currently open project
    - "open": Open a project by name. Requires: name
    - "save": Save the current project
    - "create": Create a new project. Requires: name
    - "close": Close the current project
    - "get_settings": Get project settings (FPS, resolution, etc.)
    - "set_settings": Set project settings. Requires: settings dict.
      Common keys: timelineFrameRate ("23.976", "24", "25", "29.97", "30", "50", "59.94", "60"),
      timelineResolutionWidth, timelineResolutionHeight (e.g. 3840, 2160),
      videoMonitorFormat, colorScienceMode.
      NOTE: timelineFrameRate can only be changed when NO timelines exist in the project.
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

    elif action == "get_settings":
        if err:
            return err
        keys = [
            "timelineFrameRate", "timelineResolutionWidth", "timelineResolutionHeight",
            "timelineOutputResolutionWidth", "timelineOutputResolutionHeight",
            "timelinePlaybackFrameRate", "videoBitDepth", "videoMonitorFormat",
            "colorScienceMode", "rcmPresetMode",
        ]
        result = {k: proj.GetSetting(k) for k in keys if proj.GetSetting(k) not in (None, "")}
        return _ok(settings=result)

    elif action == "set_settings":
        if err:
            return err
        if not settings:
            return _err("'settings' dict is required. Example: {\"timelineFrameRate\": \"25\"}")
        applied = {}
        failed = {}
        for key, value in settings.items():
            ok = proj.SetSetting(key, str(value))
            if ok:
                applied[key] = value
            else:
                failed[key] = value
        return _ok(applied=applied, failed=failed)

    else:
        return _err(
            f"Unknown action: {action}. "
            "Valid: list, get_current, open, save, create, close, get_settings, set_settings"
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
    - "split_at_markers": Split clips at all marker positions. Optional: name (marker color filter)
    - "delete_between_markers": Delete all clips fully within two frame positions.
      Requires: track_index (marker_a_frame), index (marker_b_frame)
    - "rename_clips_from_markers": Rename clips after nearest overlapping marker. Optional: name (color filter)
    - "delete": Delete a timeline by name. Requires: name. WARNING: irreversible.
    - "get_timecode": Get current playhead position as timecode
    - "set_timecode": Set playhead to timecode. Requires: name (timecode string "HH:MM:SS:FF")

    Args:
        track_index: Frame number when used with add_marker or delete_between_markers
        index: marker_b_frame when used with delete_between_markers
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
        marker_name = f"Marker @ {track_index}"
        result = tl.AddMarker(track_index, marker_color, marker_name, "", 1)
        return _ok(frame=track_index, color=marker_color, name=marker_name, added=result)

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

    elif action == "split_at_markers":
        if err:
            return err
        markers = tl.GetMarkers()
        if not markers:
            return _ok(splits_attempted=0, splits_succeeded=0, splits_failed=0, message="No markers found")
        color_filter = name  # name-Parameter als optionaler Farbfilter
        attempted = 0
        succeeded = 0
        failed = 0
        errors = []
        video_count = tl.GetTrackCount("video")
        # Fix I-3: SplitClip-Verfügbarkeit einmalig prüfen
        if not hasattr(tl, "SplitClip"):
            return _err("SplitClip() not available in this Resolve version. Requires Resolve 18+")
        for frame, marker_data in sorted(markers.items()):
            if color_filter and marker_data.get("color") != color_filter:
                continue
            split_ok = False
            clip_found = False
            for track_i in range(1, video_count + 1):
                items = tl.GetItemListInTrack("video", track_i)
                if not items:
                    continue
                for item in items:
                    # Fix M-1: Overlap-Bedingung vereinheitlichen (konsistent mit get_marker_clips)
                    if item.GetStart() <= frame < item.GetEnd():
                        clip_found = True
                        try:
                            result_split = tl.SplitClip(item, frame)
                            if result_split:
                                split_ok = True
                        except Exception as e:
                            errors.append(f"Frame {frame}: {e}")
            # Fix I-2: attempted nur erhöhen wenn tatsächlich ein Clip gefunden wurde
            if clip_found:
                attempted += 1
                if split_ok:
                    succeeded += 1
                else:
                    failed += 1
        return _ok(
            splits_attempted=attempted,
            splits_succeeded=succeeded,
            splits_failed=failed,
            errors=errors,
        )

    elif action == "delete_between_markers":
        if err:
            return err
        # marker_a_frame passed as track_index, marker_b_frame as index
        marker_a = track_index
        marker_b = index
        if marker_a is None or marker_b is None:
            return _err(
                "'marker_a_frame' (track_index) and 'marker_b_frame' (index) are required. "
                "Pass the frame numbers as track_index and index parameters."
            )
        if marker_a >= marker_b:
            return _err(f"marker_a_frame ({marker_a}) must be less than marker_b_frame ({marker_b})")
        video_count = tl.GetTrackCount("video")
        clips_to_delete = []
        for track_i in range(1, video_count + 1):
            items = tl.GetItemListInTrack("video", track_i)
            if not items:
                continue
            for item in items:
                start = item.GetStart()
                end = item.GetEnd()
                if start >= marker_a and end <= marker_b:
                    clips_to_delete.append(item)
        if not clips_to_delete:
            return _ok(deleted=0, message=f"No clips fully within frames {marker_a}–{marker_b}")
        result_del = tl.DeleteClips(clips_to_delete)
        return _ok(deleted=len(clips_to_delete), from_frame=marker_a, to_frame=marker_b, result=result_del)

    elif action == "rename_clips_from_markers":
        if err:
            return err
        markers = tl.GetMarkers()
        if not markers:
            return _ok(renamed=0, message="No markers found")
        color_filter = name  # name-Parameter als optionaler Farbfilter
        video_count = tl.GetTrackCount("video")
        renamed = 0
        for track_i in range(1, video_count + 1):
            items = tl.GetItemListInTrack("video", track_i)
            if not items:
                continue
            for item in items:
                clip_start = item.GetStart()
                clip_end = item.GetEnd()
                best_frame = None
                best_dist = None
                best_marker = None
                for frame, marker_data in markers.items():
                    if color_filter and marker_data.get("color") != color_filter:
                        continue
                    if clip_start <= frame < clip_end:
                        dist = abs(frame - clip_start)
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            best_frame = frame
                            best_marker = marker_data
                if best_frame is not None and best_marker and best_marker.get("name"):
                    item.SetClipProperty("Clip Name", best_marker["name"])
                    renamed += 1
        return _ok(renamed=renamed)

    elif action == "delete":
        if not name:
            return _err("'name' is required — timeline name to delete")
        pm, proj2, err2 = resolve.check()
        if err2:
            return err2
        count = proj2.GetTimelineCount()
        target = None
        for i in range(1, count + 1):
            t = proj2.GetTimelineByIndex(i)
            if t and t.GetName() == name:
                target = t
                break
        if not target:
            return _err(f"Timeline '{name}' not found")
        mp2 = proj2.GetMediaPool()
        result = mp2.DeleteTimelines([target])
        return _ok(deleted=name, result=result)

    elif action == "get_timecode":
        tc = tl.GetCurrentTimecode()
        return _ok(timecode=tc)

    elif action == "set_timecode":
        if not name:
            return _err("'name' is required — timecode string in format 'HH:MM:SS:FF'")
        import re
        if not re.match(r"^\d{2}:\d{2}:\d{2}:\d{2}$", name):
            return _err(f"Invalid timecode format '{name}'. Expected 'HH:MM:SS:FF'")
        result = tl.SetCurrentTimecode(name)
        if not result:
            return _err(f"Could not set timecode to '{name}'")
        return _ok(timecode=name)

    else:
        return _err(
            f"Unknown action: {action}. Valid: list, get_current, set_current, create, delete, "
            "get_tracks, get_items, get_markers, add_marker, delete_markers, get_settings, "
            "duplicate, add_track, delete_track, export, insert_title, insert_generator, "
            "delete_clips, get_marker_clips, split_at_markers, delete_between_markers, "
            "rename_clips_from_markers, get_timecode, set_timecode"
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
    take_index: int | None = None,
    media_pool_clip: str | None = None,
    start_frame: int | None = None,
    end_frame: int | None = None,
    cache_type: str | None = None,
    start_s: float | None = None,
    end_s: float | None = None,
    fps: float | None = None,
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
    - "get_takes": List all takes on a clip. Requires: track_type, track_index, item_index
    - "get_selected_take": Get active take index. Requires: track_type, track_index, item_index
    - "add_take": Add alternative media as take. Requires: track_type, track_index, item_index, media_pool_clip. Optional: start_frame, end_frame
    - "select_take": Switch to a take. Requires: track_type, track_index, item_index, take_index (1-based)
    - "delete_take": Remove a take. Requires: track_type, track_index, item_index, take_index (1-based)
    - "finalize_take": Finalize the active take. Requires: track_type, track_index, item_index
    - "get_cache": Get cache status. Requires: track_type, track_index, item_index
    - "set_cache": Set cache. Requires: track_type, track_index, item_index, cache_type ("color"/"fusion"), property_value ("true"/"false")
    - "update_sidecar": Update sidecar for BRAW/R3D. Requires: track_type, track_index, item_index
    - "stabilize": Apply stabilization. Requires: track_type, track_index, item_index
    - "set_cdl": Set CDL color correction. Requires: property_value ("slope;offset;power;saturation").
      Example: "0.94 0.88 0.82;-0.04 -0.03 0.0;0.95 0.95 0.95;0.75". Optional: property_name (node index, default "1")
    - "copy_grades": Copy grades from this clip to all others on same track. Requires: track_type, track_index, item_index
    - "smart_reframe": Apply AI smart reframing. Requires: track_type, track_index, item_index
    - "set_speed": Set clip playback speed (retime). Requires: property_value (speed % as string, e.g. "25" for 25% = 4x slowmo, "50" for 2x slowmo, "200" for 2x fast).
      Optional: property_name ("ripple" = "true"/"false", default "false"). 100 = normal speed.
    - "trim": Set In/Out point of a clip already on the timeline. Requires at least one of:
      start_frame/start_s (source In-point) or end_frame/end_s (source Out-point).
      Optional: fps (auto-detected from clip if omitted). track_type, track_index, item_index to identify clip.
      start_frame/end_frame = absolute source frame numbers at native clip fps.
      start_s/end_s = seconds into source clip (converted to frames via fps).

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
        take_index: Take index, 1-based (for select_take, delete_take)
        media_pool_clip: Clip name in Media Pool (for add_take)
        start_frame: Source start frame (for add_take)
        end_frame: Source end frame (for add_take)
        cache_type: Cache type "color" or "fusion" (for set_cache)
        start_s: Source In-point in seconds (for trim)
        end_s: Source Out-point in seconds (for trim)
        fps: Native clip fps for seconds conversion (for trim, auto-detected if omitted)
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

    elif action == "get_takes":
        item, item_err = _get_item()
        if item_err:
            return item_err
        count = item.GetTakesCount() if hasattr(item, "GetTakesCount") else 0
        takes = []
        for i in range(1, count + 1):
            take = item.GetTakeByIndex(i)
            takes.append({"index": i, "info": _ser(take)})
        return _ok(count=count, takes=takes)

    elif action == "get_selected_take":
        item, item_err = _get_item()
        if item_err:
            return item_err
        idx = item.GetSelectedTakeIndex() if hasattr(item, "GetSelectedTakeIndex") else 0
        return _ok(selected_take=idx)

    elif action == "add_take":
        if not media_pool_clip:
            return _err("'media_pool_clip' is required (clip name in current Media Pool folder)")
        item, item_err = _get_item()
        if item_err:
            return item_err
        # Find the MediaPoolItem by name
        proj2, mp, mp_err = resolve.get_media_pool()
        if mp_err:
            return mp_err
        folder = mp.GetCurrentFolder()
        clips = folder.GetClipList()
        mpi = None
        if clips:
            for c in clips:
                if c.GetName() == media_pool_clip:
                    mpi = c
                    break
        if not mpi:
            return _err(f"Clip '{media_pool_clip}' not found in current Media Pool folder")
        sf = start_frame or 0
        ef = end_frame or mpi.GetClipProperty("End")
        result = item.AddTake(mpi, sf, ef)
        return _ok(added=bool(result), clip=media_pool_clip)

    elif action == "select_take":
        if take_index is None:
            return _err("'take_index' is required (1-based)")
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.SelectTakeByIndex(take_index)
        return _ok(selected=bool(result), take_index=take_index)

    elif action == "delete_take":
        if take_index is None:
            return _err("'take_index' is required (1-based)")
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.DeleteTakeByIndex(take_index)
        return _ok(deleted=bool(result), take_index=take_index)

    elif action == "finalize_take":
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.FinalizeTake()
        return _ok(finalized=bool(result))

    elif action == "get_cache":
        item, item_err = _get_item()
        if item_err:
            return item_err
        color_cache = item.GetIsColorOutputCacheEnabled() if hasattr(item, "GetIsColorOutputCacheEnabled") else None
        fusion_cache = item.GetIsFusionOutputCacheEnabled() if hasattr(item, "GetIsFusionOutputCacheEnabled") else None
        return _ok(color_cache=color_cache, fusion_cache=fusion_cache)

    elif action == "set_cache":
        if not cache_type:
            return _err("'cache_type' is required ('color' or 'fusion')")
        if cache_type not in ("color", "fusion"):
            return _err(f"Invalid cache_type '{cache_type}'. Valid: color, fusion")
        if property_value is None:
            return _err("'property_value' is required ('true' or 'false')")
        item, item_err = _get_item()
        if item_err:
            return item_err
        enabled = property_value.lower() != "false"
        if cache_type == "color":
            result = item.SetColorOutputCache(enabled)
        else:
            result = item.SetFusionOutputCache(enabled)
        return _ok(cache_type=cache_type, enabled=enabled, set=bool(result))

    elif action == "update_sidecar":
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.UpdateSidecar() if hasattr(item, "UpdateSidecar") else False
        return _ok(updated=bool(result))

    elif action == "stabilize":
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.Stabilize() if hasattr(item, "Stabilize") else False
        return _ok(stabilized=bool(result))

    elif action == "set_cdl":
        # Set CDL (Color Decision List) correction on a clip
        # property_value format: "slope_r slope_g slope_b;offset_r offset_g offset_b;power_r power_g power_b;saturation"
        # Example: "0.94 0.88 0.82;-0.04 -0.035 -0.005;0.92 0.94 0.98;0.72"
        if not property_value:
            return _err(
                "'property_value' is required — format: 'slope_r slope_g slope_b;offset_r offset_g offset_b;"
                "power_r power_g power_b;saturation'. Example: '0.94 0.88 0.82;-0.04 -0.03 0.0;0.95 0.95 0.95;0.75'"
            )
        item, item_err = _get_item()
        if item_err:
            return item_err
        parts = property_value.split(";")
        if len(parts) != 4:
            return _err("CDL needs 4 parts separated by ';': slope;offset;power;saturation")
        cdl = {
            "NodeIndex": str(property_name or "1"),
            "Slope": parts[0].strip(),
            "Offset": parts[1].strip(),
            "Power": parts[2].strip(),
            "Saturation": parts[3].strip(),
        }
        result = item.SetCDL(cdl)
        return _ok(cdl=cdl, applied=bool(result))

    elif action == "copy_grades":
        # Copy grades from the source clip to all other clips on the same track
        item, item_err = _get_item()
        if item_err:
            return item_err
        tt = track_type or "video"
        ti = track_index or 1
        all_items = tl.GetItemListInTrack(tt, ti)
        if not all_items:
            return _err(f"No items on {tt} track {ti}")
        targets = [it for it in all_items if it != item]
        if not targets:
            return _err("No other clips to copy grades to")
        result = item.CopyGrades(targets)
        return _ok(copied=bool(result), source_index=item_index, target_count=len(targets))

    elif action == "smart_reframe":
        # Apply AI-based smart reframing to a clip
        item, item_err = _get_item()
        if item_err:
            return item_err
        result = item.SmartReframe()
        return _ok(reframed=bool(result))

    elif action == "set_speed":
        if property_value is None:
            return _err("'property_value' is required — speed percentage as string (e.g. '25' for 4x slowmo, '100' for normal)")
        item, item_err = _get_item()
        if item_err:
            return item_err
        try:
            speed = float(property_value)
        except ValueError:
            return _err(f"'property_value' must be a number, got '{property_value}'")
        ripple = (property_name or "false").lower() == "true"
        result = item.ChangeClipSpeed(speed, ripple)
        return _ok(item=item.GetName(), speed=speed, ripple=ripple, applied=bool(result))

    elif action == "trim":
        item, item_err = _get_item()
        if item_err:
            return item_err
        if start_frame is None and start_s is None and end_frame is None and end_s is None:
            return _err("trim requires at least one of: start_frame, start_s, end_frame, end_s")

        # Resolve fps: explicit > auto-detect from source clip
        clip_fps = fps
        if clip_fps is None:
            try:
                source = item.GetSourceItem()
                fps_str = source.GetClipProperty("FPS") if source else None
                clip_fps = float(fps_str) if fps_str else 25.0
            except Exception:
                clip_fps = 25.0

        # Convert seconds to frames
        sf = start_frame
        ef = end_frame
        if start_s is not None and sf is None:
            sf = int(start_s * clip_fps)
        if end_s is not None and ef is None:
            ef = int(end_s * clip_fps)

        applied_left = None
        applied_right = None

        if sf is not None:
            result = item.SetLeftOffset(sf)
            if result is False:
                return _err(f"SetLeftOffset({sf}) fehlgeschlagen — Offset außerhalb des Source-Clips?")
            applied_left = sf

        if ef is not None:
            try:
                source = item.GetSourceItem()
                total_str = source.GetClipProperty("Frames") if source else None
                total_frames = int(total_str) if total_str else None
            except Exception:
                total_frames = None

            if total_frames is None:
                return _err("Konnte Gesamtframe-Anzahl des Source-Clips nicht ermitteln — end_frame/end_s nicht anwendbar")

            right_offset = total_frames - ef - 1
            if right_offset < 0:
                return _err(f"end_frame {ef} liegt außerhalb des Source-Clips ({total_frames} Frames)")
            result = item.SetRightOffset(right_offset)
            if result is False:
                return _err(f"SetRightOffset({right_offset}) fehlgeschlagen — Offset außerhalb des Source-Clips?")
            applied_right = right_offset

        return _ok(
            item=item.GetName(),
            left_offset_set=applied_left,
            right_offset_set=applied_right,
            fps_used=clip_fps,
        )

    else:
        return _err(
            f"Unknown action: {action}. Valid: get_current, get_properties, set_property, "
            "get_info, set_clip_color, clear_clip_color, set_enabled, get_source_info, "
            "get_takes, get_selected_take, add_take, select_take, delete_take, finalize_take, "
            "get_cache, set_cache, update_sidecar, stabilize, set_cdl, copy_grades, smart_reframe, "
            "set_speed, trim"
        )


# ── media_pool ──────────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def media_pool(
    action: str,
    folder_name: str | None = None,
    file_paths: list[str] | None = None,
    timeline_name: str | None = None,
    start_frame: int | None = None,
    end_frame: int | None = None,
    duration_s: float | None = None,
    start_s: float | None = None,
    fps: float | None = None,
    clip_specs: str | None = None,
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
    - "append_to_timeline": Append clips from current folder to active timeline.
      Optional: file_paths (clip names to filter).
      Trim support (single clip): start_frame/end_frame (source frame numbers at native fps),
      OR start_s/duration_s (seconds, requires fps parameter or auto-detected from clip).
      Multi-clip trim: clip_specs (JSON array, see below). Overrides file_paths/start_frame/etc.
      clip_specs format: '[{"name":"clip.mp4","start_s":10,"duration_s":5},{"name":"b.mp4"}]'
      Per-clip fields: name (required), start_frame, end_frame, start_s, duration_s, fps.

    Args:
        action: The action to perform
        folder_name: Folder name (for set/create/delete_folder) or clip name (for get_clip_info)
        file_paths: List of absolute file paths (for import_media) or clip names (for append_to_timeline)
        timeline_name: Name for new timeline (for create_timeline_from_clips)
        start_frame: Source start frame (for append_to_timeline trim, at native clip fps)
        end_frame: Source end frame inclusive (for append_to_timeline trim, at native clip fps)
        duration_s: Duration in seconds to take from clip (alternative to end_frame)
        start_s: Start offset in seconds into clip (alternative to start_frame)
        fps: Native clip fps for second-based calculations (auto-detected if omitted)
        clip_specs: JSON array of clip dicts for multi-clip trim (overrides single-clip trim params)
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

        # ── Multi-clip trim via clip_specs JSON ──────────────────
        if clip_specs is not None:
            import json as _json
            try:
                specs = _json.loads(clip_specs)
            except _json.JSONDecodeError as e:
                return _err(f"clip_specs ist kein gültiges JSON: {e}")

            current = mp.GetCurrentFolder()
            all_clips = current.GetClipList() if current else []
            clip_by_name = {c.GetName(): c for c in all_clips}

            clip_infos = []
            resolved = []
            for spec in specs:
                name = spec.get("name")
                if not name:
                    return _err(f"Jeder clip_specs-Eintrag benötigt 'name'. Ungültig: {spec}")
                clip = clip_by_name.get(name)
                if clip is None:
                    return _err(f"Clip '{name}' nicht gefunden. Verfügbar: {list(clip_by_name.keys())}")

                # Resolve fps: per-spec > auto-detect
                clip_fps = spec.get("fps")
                if clip_fps is None:
                    try:
                        fps_str = clip.GetClipProperty("FPS")
                        clip_fps = float(fps_str) if fps_str else 25.0
                    except (ValueError, TypeError):
                        clip_fps = 25.0

                sf = spec.get("start_frame")
                ef = spec.get("end_frame")
                ss = spec.get("start_s")
                ds = spec.get("duration_s")

                if ss is not None and sf is None:
                    sf = int(ss * clip_fps)
                if ds is not None and ef is None:
                    base = sf if sf is not None else 0
                    ef = base + int(ds * clip_fps) - 1

                info = {"mediaPoolItem": clip}
                if sf is not None:
                    info["startFrame"] = sf
                if ef is not None:
                    info["endFrame"] = ef
                clip_infos.append(info)
                resolved.append({"name": name, "start_frame": sf, "end_frame": ef, "fps_used": clip_fps})

            result = mp.AppendToTimeline(clip_infos)
            if result is None or (isinstance(result, list) and len(result) == 0):
                return _err("AppendToTimeline fehlgeschlagen — ist eine Timeline aktiv?")
            return _ok(appended=len(clip_infos), clips=resolved)

        # ── Bisheriger Single-Clip-Pfad (rückwärts-kompatibel) ───
        current = mp.GetCurrentFolder()
        clips = current.GetClipList() if current else []
        if not clips:
            return _err("No clips in the current folder")
        if file_paths:
            selected = [c for c in clips if c.GetName() in file_paths]
            if not selected:
                return _err(f"No matching clips found. Available: {[c.GetName() for c in clips]}")
        else:
            selected = clips

        use_trim = (start_frame is not None or end_frame is not None or
                    start_s is not None or duration_s is not None)

        if use_trim:
            if len(selected) != 1:
                return _err("Trim (start_frame/end_frame/start_s/duration_s) requires exactly one clip — filter with file_paths")
            clip = selected[0]
            clip_fps = fps
            if clip_fps is None:
                fps_str = clip.GetClipProperty("FPS")
                try:
                    clip_fps = float(fps_str) if fps_str else 25.0
                except (ValueError, TypeError):
                    clip_fps = 25.0

            sf = start_frame
            ef = end_frame
            if start_s is not None and sf is None:
                sf = int(start_s * clip_fps)
            if duration_s is not None and ef is None:
                base = sf if sf is not None else 0
                ef = base + int(duration_s * clip_fps) - 1

            clip_info = {"mediaPoolItem": clip}
            if sf is not None:
                clip_info["startFrame"] = sf
            if ef is not None:
                clip_info["endFrame"] = ef

            result = mp.AppendToTimeline([clip_info])
            if result is None or (isinstance(result, list) and len(result) == 0):
                return _err("AppendToTimeline failed — check if a timeline is active")
            return _ok(
                appended=1,
                clip_names=[clip.GetName()],
                start_frame=sf,
                end_frame=ef,
                clip_fps=clip_fps,
            )
        else:
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
            "create_timeline_from_clips, get_root_folder, selected_clips, "
            "append_to_timeline (single-clip: start_frame/end_frame/start_s/duration_s; multi-clip: clip_specs JSON)"
        )


# ── color ───────────────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def color(
    action: str,
    node_index: int | None = None,
    lut_path: str | None = None,
    item_index: int | None = None,
    version_name: str | None = None,
    version_type: int | None = None,
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
    - "list_versions": List color versions. Optional: version_type (0=local, 1=remote, default 0)
    - "get_version": Get current color version
    - "add_version": Create a color version. Requires: version_name. Optional: version_type (0=local, 1=remote, default 0)
    - "load_version": Switch to a version. Requires: version_name. Optional: version_type (default 0)
    - "delete_version": Delete a version. Requires: version_name. Optional: version_type (default 0)
    - "create_magic_mask": Create magic mask. Requires: lut_path (mode: "F"=Forward, "B"=Backward, "BI"=Bidirectional)
    - "regenerate_magic_mask": Regenerate existing magic mask
    - "export_lut": Export LUT from clip. Requires: node_index (0=.cube, 1=.3dl), lut_path (output file path)
    - "grab_and_analyze": Grab the current frame and analyze luma/color. Returns metrics + suggested CDL power.
    - "analyze_timeline": Measure all clips on video track 1. Returns luma + suggested CDL power for every clip automatically.
    - "auto_grade": Measure ALL clips and apply CDL Power in one step. Optional: node_index as target luma (default 0.38).

    Args:
        node_index: 1-based node index; exception: for export_lut use 0=.cube or 1=.3dl
        lut_path: For set_node_enabled: "true"/"false" instead of a LUT path
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

    elif action == "list_versions":
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        vt = version_type if version_type is not None else 0
        versions = item.GetVersionNameList(vt) if hasattr(item, "GetVersionNameList") else []
        return _ok(versions=versions or [], version_type=vt)

    elif action == "get_version":
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        version = item.GetCurrentVersion() if hasattr(item, "GetCurrentVersion") else None
        return _ok(version=_ser(version))

    elif action == "add_version":
        if not version_name:
            return _err("'version_name' is required")
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        vt = version_type if version_type is not None else 0
        result = item.AddVersion(version_name, vt)
        return _ok(added=bool(result), version_name=version_name, version_type=vt)

    elif action == "load_version":
        if not version_name:
            return _err("'version_name' is required")
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        vt = version_type if version_type is not None else 0
        result = item.LoadVersionByName(version_name, vt)
        return _ok(loaded=bool(result), version_name=version_name)

    elif action == "delete_version":
        if not version_name:
            return _err("'version_name' is required")
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        vt = version_type if version_type is not None else 0
        result = item.DeleteVersionByName(version_name, vt)
        return _ok(deleted=bool(result), version_name=version_name)

    elif action == "create_magic_mask":
        if not lut_path:
            return _err("'lut_path' is required as mode: 'F' (Forward), 'B' (Backward), 'BI' (Bidirectional)")
        if lut_path not in ("F", "B", "BI"):
            return _err(f"Invalid mode '{lut_path}'. Valid: F, B, BI")
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        result = item.CreateMagicMask(lut_path)
        return _ok(created=bool(result), mode=lut_path)

    elif action == "regenerate_magic_mask":
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        result = item.RegenerateMagicMask() if hasattr(item, "RegenerateMagicMask") else False
        return _ok(regenerated=bool(result))

    elif action == "export_lut":
        if node_index is None:
            return _err("'node_index' is required (export type: 0=.cube, 1=.3dl)")
        if not lut_path:
            return _err("'lut_path' is required (output file path)")
        if node_index not in (0, 1):
            return _err(f"Invalid node_index '{node_index}' as export type. Valid: 0 (.cube), 1 (.3dl)")
        if err:
            return err
        item = tl.GetCurrentVideoItem()
        if not item:
            return _err("No current video item")
        result = item.ExportLUT(node_index, lut_path)
        return _ok(exported=bool(result), path=lut_path)

    elif action == "grab_and_analyze":
        # Analyze current frame via ffmpeg on source clip (bypasses Resolve Gallery API)
        if err:
            return err

        import os as _os
        import math as _math
        import subprocess as _subprocess
        import tempfile as _tempfile
        import json as _json
        import shutil as _shutil

        # Get source file path and timecode from current timeline item
        items = tl.GetItemListInTrack("video", 1)
        if not items:
            return _err("No clips on video track 1")

        # Find which item covers the current playhead
        tc_str = tl.GetCurrentTimecode()
        # Convert timecode to frame number
        settings = tl.GetSetting()
        fps_str = settings.get("timelineFrameRate", "24")
        try:
            fps = float(fps_str)
        except Exception:
            fps = 24.0

        cur_frame = tc_to_frames(tc_str, fps)

        current_item = None
        for item in items:
            start = item.GetStart()
            end = item.GetEnd()
            if start <= cur_frame < end:
                current_item = item
                break
        if current_item is None:
            current_item = items[0]

        media = current_item.GetMediaPoolItem()
        if not media:
            return _err("Cannot get MediaPoolItem for current clip")
        clip_path = media.GetClipProperty("File Path")
        if not clip_path or not _os.path.exists(clip_path):
            return _err(f"Source file not found: {clip_path}")

        # Compute offset within the clip (in seconds)
        item_start = current_item.GetStart()
        clip_offset_frames = max(0, cur_frame - item_start)
        clip_start_frame = current_item.GetSourceStartFrame() if hasattr(current_item, "GetSourceStartFrame") else 0
        source_frame = clip_start_frame + clip_offset_frames
        offset_sec = source_frame / fps

        # Extract frame with ffmpeg, analyze luma via signalstats filter
        ffmpeg = _shutil.which("ffmpeg")
        if not ffmpeg:
            return _err("ffmpeg not found in PATH. Install via: brew install ffmpeg")

        # Find LUT for post-LUT Rec709 measurement
        lut_path = None
        try:
            lut_rel = current_item.GetLUT(1) if hasattr(current_item, "GetLUT") else None
            lut_path = find_lut(lut_rel)
        except Exception:
            pass

        out_png = _os.path.join(_tempfile.gettempdir(), "resolve_analyze_frame.png")
        try:
            cmd = [ffmpeg, "-y", "-ss", str(offset_sec), "-i", clip_path]
            if lut_path:
                safe_lut = lut_path.replace("\\", "/").replace(":", "\\:")
                cmd += ["-vf", f"lut3d='{safe_lut}'"]
            cmd += ["-vframes", "1", "-q:v", "2", out_png]
            _subprocess.run(cmd, capture_output=True, timeout=15)
            if not _os.path.exists(out_png):
                return _err(f"ffmpeg could not extract frame from {clip_path} at {offset_sec:.2f}s")

            import numpy as np
            from PIL import Image

            img = Image.open(out_png).convert("RGB")
            if img.width > 1920:
                img = img.resize((1920, 1080), Image.BILINEAR)
            arr = np.array(img, dtype=np.float32) / 255.0

            r_ch, g_ch, b_ch = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
            luma = 0.2126 * r_ch + 0.7152 * g_ch + 0.0722 * b_ch

            valid = luma > 0.02
            if valid.sum() > luma.size * 0.3:
                luma_v = luma[valid]
                r_v, g_v, b_v = r_ch[valid], g_ch[valid], b_ch[valid]
            else:
                luma_v, r_v, g_v, b_v = luma.ravel(), r_ch.ravel(), g_ch.ravel(), b_ch.ravel()
            mean_luma = float(np.mean(luma_v))
            r_mean = float(np.mean(r_v))
            g_mean = float(np.mean(g_v))
            b_mean = float(np.mean(b_v))
            p05 = float(np.percentile(luma_v, 5))
            p95 = float(np.percentile(luma_v, 95))
            shadow_pct = float(np.mean(luma_v < 0.20) * 100)
            mid_pct = float(np.mean((luma_v >= 0.20) & (luma_v < 0.70)) * 100)
            hi_pct = float(np.mean(luma_v >= 0.70) * 100)
            crop_pct = round(100.0 * (1.0 - valid.sum() / luma.size), 1)

            TARGET_LUMA = 0.38
            if 0.005 < mean_luma < 0.995:
                sug_power = round(_math.log(TARGET_LUMA) / _math.log(mean_luma), 3)
                sug_power = max(0.50, min(1.80, sug_power))
            else:
                sug_power = 1.0

            assessment = (
                "too_dark" if mean_luma < 0.20 else
                "slightly_dark" if mean_luma < 0.33 else
                "good" if mean_luma < 0.50 else
                "bright"
            )

        finally:
            try:
                _os.remove(out_png)
            except Exception:
                pass

        return _ok(
            source="ffmpeg",
            clip_path=clip_path,
            offset_sec=round(offset_sec, 2),
            mean_luma=round(mean_luma, 3),
            luma_p05=round(p05, 3),
            luma_p95=round(p95, 3),
            channels=dict(r=round(r_mean, 3), g=round(g_mean, 3), b=round(b_mean, 3)),
            zones=dict(shadows=round(shadow_pct, 1), midtones=round(mid_pct, 1), highlights=round(hi_pct, 1)),
            assessment=assessment,
            suggested_power=f"{sug_power:.3f} {sug_power:.3f} {sug_power:.3f}",
            note=f"Luma measured {'post-LUT (Rec709)' if lut_path else 'on DLog source (no LUT found)'}",
            lut_applied=_os.path.basename(lut_path) if lut_path else None,
            black_border_pct=crop_pct,
        )

    elif action == "analyze_timeline":
        # Measure all clips on video track 1 and return luma stats + suggested CDL power for each
        if err:
            return err

        import os as _os
        import math as _math
        import subprocess as _subprocess
        import tempfile as _tempfile
        import shutil as _shutil

        items = tl.GetItemListInTrack("video", 1)
        if not items:
            return _err("No clips on video track 1")

        settings = tl.GetSetting()
        fps_str = settings.get("timelineFrameRate", "24")
        try:
            fps = float(fps_str)
        except Exception:
            fps = 24.0

        # Timeline start offset in frames (e.g. 01:00:00:00 = 90000 frames at 25fps)
        tl_start_tc = tl.GetStartTimecode() if hasattr(tl, "GetStartTimecode") else "01:00:00:00"
        tl_start_frame = tc_to_frames(tl_start_tc, fps)

        ffmpeg = _shutil.which("ffmpeg")
        if not ffmpeg:
            return _err("ffmpeg not found in PATH. Install via: brew install ffmpeg")

        TARGET_LUMA = 0.38

        # Try to get LUT from first clip node 1
        first_items = tl.GetItemListInTrack("video", 1) or []
        applied_lut_path = None
        if first_items:
            try:
                first_grade = first_items[0].GetNodeGraph(1) if hasattr(first_items[0], "GetNodeGraph") else None
                # Use color tool to get LUT path
                lut_rel = first_items[0].GetLUT(1) if hasattr(first_items[0], "GetLUT") else None
                applied_lut_path = find_lut(lut_rel)
            except Exception:
                pass

        out_png = _os.path.join(_tempfile.gettempdir(), "resolve_analyze_frame.png")

        def _source_offset_sec(item, fps):
            """Return the correct source-file seek time in seconds for the clip's mid-frame.
            Uses GetLeftOffset() (= in-point offset from clip start) when available,
            so clips that were trimmed at the in-point are measured correctly."""
            tl_start = item.GetStart()
            tl_end   = item.GetEnd()
            tl_mid   = (tl_start + tl_end) // 2
            clip_frames_from_head = tl_mid - tl_start   # frames into this clip from its in-point

            # GetLeftOffset() = how many frames were trimmed off the front of the source
            left_offset = 0
            try:
                left_offset = int(item.GetLeftOffset())
            except Exception:
                pass

            source_frame = left_offset + clip_frames_from_head
            return max(0.0, source_frame / fps)

        def _measure_frame_v2(clip_path, offset_sec, lut_path):
            cmd = [ffmpeg, "-y", "-ss", str(offset_sec), "-i", clip_path]
            if lut_path:
                safe = lut_path.replace("\\", "/").replace(":", "\\:")
                cmd += ["-vf", f"lut3d='{safe}'"]
            cmd += ["-vframes", "1", "-q:v", "2", out_png]
            _subprocess.run(cmd, capture_output=True, timeout=15)
            if not _os.path.exists(out_png):
                return None
            try:
                import numpy as np
                from PIL import Image
                img = Image.open(out_png).convert("RGB")
                if img.width > 1920:
                    img = img.resize((1920, 1080), Image.BILINEAR)
                arr = np.array(img, dtype=np.float32) / 255.0
                r_ch, g_ch, b_ch = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
                luma = 0.2126 * r_ch + 0.7152 * g_ch + 0.0722 * b_ch
                valid = luma > 0.02
                luma_v = luma[valid] if valid.sum() > luma.size * 0.3 else luma.ravel()
                crop_pct = round(100.0 * (1.0 - valid.sum() / luma.size), 1)
                return {
                    "mean": float(np.mean(luma_v)),
                    "p05":  float(np.percentile(luma_v, 5)),
                    "p95":  float(np.percentile(luma_v, 95)),
                    "crop_pct": crop_pct,
                }
            finally:
                try:
                    _os.remove(out_png)
                except Exception:
                    pass

        def _analyze_clip(item, idx):
            media = item.GetMediaPoolItem()
            if not media:
                return {"clip": idx, "error": "no MediaPoolItem"}
            clip_path = media.GetClipProperty("File Path")
            if not clip_path or not _os.path.exists(clip_path):
                return {"clip": idx, "error": f"file not found: {clip_path}"}

            offset_sec = _source_offset_sec(item, fps)

            # Per-clip LUT lookup (fallback to pre-resolved applied_lut_path)
            lut_path = applied_lut_path
            if lut_path is None:
                try:
                    lut_rel = item.GetLUT(1) if hasattr(item, "GetLUT") else None
                    lut_path = find_lut(lut_rel)
                except Exception:
                    pass

            stats = _measure_frame_v2(clip_path, offset_sec, lut_path)
            if stats is None:
                return {"clip": idx, "error": f"ffmpeg failed at {offset_sec:.2f}s"}

            mean_luma = stats["mean"]
            if 0.005 < mean_luma < 0.995:
                sug_power = round(_math.log(TARGET_LUMA) / _math.log(mean_luma), 3)
                sug_power = max(0.50, min(1.80, sug_power))
            else:
                sug_power = 1.0

            # Timeline mid-frame → timecode string
            tl_mid = (item.GetStart() + item.GetEnd()) // 2
            total_sec = tl_mid / fps
            h = int(total_sec // 3600)
            m = int((total_sec % 3600) // 60)
            s = int(total_sec % 60)
            f = int(round((total_sec % 1) * fps))
            tc = f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

            return {
                "clip": idx,
                "timecode": tc,
                "clip_path": _os.path.basename(clip_path),
                "offset_sec": round(offset_sec, 2),
                "mean_luma": round(mean_luma, 3),
                "luma_p05": round(stats["p05"], 3),
                "luma_p95": round(stats["p95"], 3),
                "black_border_pct": stats.get("crop_pct", 0.0),
                "suggested_power": f"{sug_power:.3f} {sug_power:.3f} {sug_power:.3f}",
                "_item": item,   # kept for auto_grade, stripped before return
                "_power": sug_power,
            }

        results = []
        for idx, item in enumerate(items, start=1):
            results.append(_analyze_clip(item, idx))

        # Strip internal keys before returning
        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]

        return _ok(
            clip_count=len(clean),
            target_luma=TARGET_LUMA,
            note=f"Luma measured {'post-LUT (Rec709)' if applied_lut_path else 'on DLog source (no LUT found)'}. suggested_power targets mean_luma={TARGET_LUMA}",
            lut_applied=_os.path.basename(applied_lut_path) if applied_lut_path else None,
            clips=clean
        )

    elif action == "auto_grade":
        # Measure all clips + apply CDL Power in one step
        if err:
            return err

        import os as _os
        import math as _math
        import subprocess as _subprocess
        import tempfile as _tempfile
        import shutil as _shutil

        items = tl.GetItemListInTrack("video", 1)
        if not items:
            return _err("No clips on video track 1")

        settings = tl.GetSetting()
        try:
            fps = float(settings.get("timelineFrameRate", "24"))
        except Exception:
            fps = 24.0

        ffmpeg = _shutil.which("ffmpeg")
        if not ffmpeg:
            return _err("ffmpeg not found in PATH. Install via: brew install ffmpeg")

        TARGET_LUMA = float(node_index) if node_index and str(node_index).replace(".", "").isdigit() else 0.38

        # Resolve LUT once from first clip
        applied_lut = None
        try:
            lut_rel = items[0].GetLUT(1) if hasattr(items[0], "GetLUT") else None
            applied_lut = find_lut(lut_rel)
        except Exception:
            pass

        out_png = _os.path.join(_tempfile.gettempdir(), "resolve_autograde_frame.png")
        applied = []

        for idx, item in enumerate(items, start=1):
            media = item.GetMediaPoolItem()
            if not media:
                applied.append({"clip": idx, "error": "no MediaPoolItem"})
                continue
            clip_path = media.GetClipProperty("File Path")
            if not clip_path or not _os.path.exists(clip_path):
                applied.append({"clip": idx, "error": f"file not found: {clip_path}"})
                continue

            # Correct source offset using in-point trim
            tl_start = item.GetStart()
            tl_end   = item.GetEnd()
            tl_mid   = (tl_start + tl_end) // 2
            left_offset = 0
            try:
                left_offset = int(item.GetLeftOffset())
            except Exception:
                pass
            source_frame = left_offset + (tl_mid - tl_start)
            offset_sec = max(0.0, source_frame / fps)

            # Per-clip LUT
            lut_path = applied_lut
            if lut_path is None:
                try:
                    lut_rel = item.GetLUT(1) if hasattr(item, "GetLUT") else None
                    lut_path = find_lut(lut_rel)
                except Exception:
                    pass

            # Extract + measure frame
            cmd = [ffmpeg, "-y", "-ss", str(offset_sec), "-i", clip_path]
            if lut_path:
                safe = lut_path.replace("\\", "/").replace(":", "\\:")
                cmd += ["-vf", f"lut3d='{safe}'"]
            cmd += ["-vframes", "1", "-q:v", "2", out_png]
            _subprocess.run(cmd, capture_output=True, timeout=15)

            if not _os.path.exists(out_png):
                applied.append({"clip": idx, "error": f"ffmpeg failed at {offset_sec:.2f}s"})
                continue

            mean_luma = 0.0
            crop_pct = 0.0
            try:
                import numpy as np
                from PIL import Image
                img = Image.open(out_png).convert("RGB")
                if img.width > 1920:
                    img = img.resize((1920, 1080), Image.BILINEAR)
                arr = np.array(img, dtype=np.float32) / 255.0
                luma = 0.2126 * arr[:,:,0] + 0.7152 * arr[:,:,1] + 0.0722 * arr[:,:,2]
                valid = luma > 0.02
                mean_luma = float(np.mean(luma[valid])) if valid.sum() > luma.size * 0.3 else float(np.mean(luma))
                crop_pct = round(100.0 * (1.0 - valid.sum() / luma.size), 1)
            finally:
                try:
                    _os.remove(out_png)
                except Exception:
                    pass

            if 0.005 < mean_luma < 0.995:
                power = round(_math.log(TARGET_LUMA) / _math.log(mean_luma), 3)
                power = max(0.50, min(1.80, power))
            else:
                power = 1.0

            # Navigate playhead to this clip and apply CDL
            tl.SetCurrentTimecode(f"{int(tl_mid // (fps * 3600)):02d}:{int((tl_mid // fps % 3600) // 60):02d}:{int(tl_mid // fps % 60):02d}:{int(tl_mid % fps):02d}")
            cdl_str = f"1.0 1.0 1.0;0.0 0.0 0.0;{power:.3f} {power:.3f} {power:.3f};1.0"
            cdl_ok = item.SetCDL({
                "NodeIndex": "1",
                "Slope": "1.0 1.0 1.0",
                "Offset": "0.0 0.0 0.0",
                "Power": f"{power:.3f} {power:.3f} {power:.3f}",
                "Saturation": "1.0"
            }) if hasattr(item, "SetCDL") else False

            applied.append({
                "clip": idx,
                "mean_luma_before": round(mean_luma, 3),
                "power_applied": f"{power:.3f} {power:.3f} {power:.3f}",
                "cdl_set": bool(cdl_ok),
                "black_border_pct": crop_pct,
            })

        return _ok(
            clip_count=len(applied),
            target_luma=TARGET_LUMA,
            lut_applied=_os.path.basename(applied_lut) if applied_lut else None,
            note=f"Measured {'post-LUT (Rec709)' if applied_lut else 'DLog source'}. CDL Power applied to node 1 of each clip.",
            clips=applied
        )

    else:
        return _err(
            f"Unknown action: {action}. Valid: get_current_item, get_node_graph, get_nodes, "
            "get_lut, set_lut, set_node_enabled, reset_grades, get_color_groups, get_timeline_nodes, "
            "list_versions, get_version, add_version, load_version, delete_version, "
            "create_magic_mask, regenerate_magic_mask, export_lut, grab_and_analyze, analyze_timeline, auto_grade"
        )


# ── analyze_media ───────────────────────────────────────────────────

@mcp.tool()
@safe_tool
def analyze_media(
    file_path: str,
    action: str = "overview",
    scene_threshold: float = 0.40,
    sample_interval: int = 90,
) -> dict:
    """Analyze a media file for intelligent editing and grading decisions.

    Uses ffprobe and ffmpeg — no Resolve connection required.

    Actions:
    - "overview": Duration, fps, resolution, codec, bitrate
    - "scenes": Detect scene/shot changes. Optional: scene_threshold (0.1–0.9, lower = more sensitive, default 0.4)
    - "brightness": Sample luma at regular intervals to find dark/bright segments.
                    Optional: sample_interval (every N frames, default 90)
    - "full": All of the above combined

    Args:
        file_path: Absolute path to the media file
        action: What to analyze (overview | scenes | brightness | full)
        scene_threshold: Scene detection sensitivity 0.1–0.9 (default 0.4)
        sample_interval: Sample every N frames for brightness analysis (default 90)
    """
    import subprocess
    import json
    import os
    import re
    import shutil as _shutil

    if not os.path.exists(file_path):
        return _err(f"File not found: {file_path}")

    ffprobe = _shutil.which("ffprobe")
    ffmpeg = _shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        missing = ", ".join(t for t, v in [("ffprobe", ffprobe), ("ffmpeg", ffmpeg)] if not v)
        return _err(f"{missing} not found in PATH. Install via: brew install ffmpeg")

    result: dict = {}

    # ── overview ────────────────────────────────────────────────────
    if action in ("overview", "full"):
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", file_path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return _err(f"ffprobe failed: {r.stderr[:300]}")
        info = json.loads(r.stdout)
        vs = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        fmt = info.get("format", {})
        if vs:
            num, den = (int(x) for x in vs.get("r_frame_rate", "30/1").split("/"))
            fps = num / den if den else 30.0
            duration = float(fmt.get("duration", 0))
            result["overview"] = {
                "duration_s": round(duration, 2),
                "fps": round(fps, 3),
                "total_frames": int(fps * duration),
                "resolution": f"{vs.get('width')}x{vs.get('height')}",
                "codec": vs.get("codec_name"),
                "bitrate_mbps": round(int(fmt.get("bit_rate", 0)) / 1_000_000, 2),
            }

    # ── scene detection ─────────────────────────────────────────────
    if action in ("scenes", "full"):
        cmd = [ffmpeg, "-i", file_path,
               "-vf", f"scdet=threshold={scene_threshold}",
               "-f", "null", "-"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        timestamps = []
        for line in r.stderr.splitlines():
            m = re.search(r"lavfi\.scd\.time=([\d.]+)", line)
            if not m:
                m = re.search(r"pts_time:([\d.]+).*?score", line)
            if m:
                t = round(float(m.group(1)), 2)
                if not timestamps or t - timestamps[-1] > 0.5:
                    timestamps.append(t)
        duration = result.get("overview", {}).get("duration_s", 0)
        result["scenes"] = {
            "count": len(timestamps),
            "cut_times_s": timestamps,
            "avg_scene_s": round(duration / max(len(timestamps) + 1, 1), 1),
        }

    # ── brightness sampling ─────────────────────────────────────────
    if action in ("brightness", "full"):
        fps = result.get("overview", {}).get("fps", 29.97)
        duration = result.get("overview", {}).get("duration_s", 0)
        if not duration:
            cmd = [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
                   "-print_format", "json", file_path]
            r = subprocess.run(cmd, capture_output=True, text=True)
            duration = float(json.loads(r.stdout).get("format", {}).get("duration", 0))

        cmd = [
            ffmpeg, "-i", file_path,
            "-vf", f"select='not(mod(n\\,{sample_interval}))',signalstats",
            "-f", "null", "-"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        samples = []
        for line in r.stderr.splitlines():
            m = re.search(r"YAVG=([\d.]+)", line)
            if m:
                samples.append(round(float(m.group(1)) / 255.0, 3))

        if samples:
            interval_s = sample_interval / fps
            timestamped = [
                {"t_s": round(i * interval_s, 1), "luma": v}
                for i, v in enumerate(samples)
            ]
            result["brightness"] = {
                "sample_count": len(samples),
                "mean_luma": round(sum(samples) / len(samples), 3),
                "min_luma": round(min(samples), 3),
                "max_luma": round(max(samples), 3),
                "dynamic_range": round(max(samples) - min(samples), 3),
                "dark_segments": [
                    s for s in timestamped if s["luma"] < 0.25
                ],
                "samples": timestamped,
            }

    return _ok(**result)


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
    enabled: bool | None = None,
    amount: int | None = None,
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
    - "get_voice_isolation": Get voice isolation state. Requires: track_index, item_index (1-based)
    - "set_voice_isolation": Set voice isolation. Requires: track_index, item_index (1-based), enabled (bool). Optional: amount (0-100)
    - "get_audio_mapping": Get source audio channel mapping. Requires: track_index, item_index (1-based)

    Args:
        action: The action to perform
        track_index: Audio track index, 1-based
        item_index: Clip index within the track, 1-based
        volume: Volume in dB (e.g. -6.0)
        muted: True to mute, False to unmute
        pan: Pan position (-1.0 = full left, 0.0 = center, 1.0 = full right)
        duration: Fade duration in frames
        enabled: Enable/disable voice isolation (for set_voice_isolation)
        amount: Voice isolation amount 0-100 (for set_voice_isolation)
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

    elif action == "get_voice_isolation":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        state = item.GetVoiceIsolationState() if hasattr(item, "GetVoiceIsolationState") else None
        return _ok(track_index=track_index, item_index=item_index, voice_isolation=_ser(state))

    elif action == "set_voice_isolation":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        if enabled is None:
            return _err("'enabled' is required (true/false)")
        if amount is not None and (amount < 0 or amount > 100):
            return _err("'amount' must be between 0 and 100")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        state = {"enabled": enabled}
        if amount is not None:
            state["amount"] = amount
        result = item.SetVoiceIsolationState(state) if hasattr(item, "SetVoiceIsolationState") else False
        return _ok(track_index=track_index, item_index=item_index, set=bool(result), **state)

    elif action == "get_audio_mapping":
        if track_index is None or item_index is None:
            return _err("'track_index' and 'item_index' are required (1-based)")
        items = tl.GetItemListInTrack("audio", track_index)
        if items is None:
            return _err(f"Could not get items from audio track {track_index}")
        items = list(items)
        if item_index < 1 or item_index > len(items):
            return _err(f"item_index {item_index} out of range (1–{len(items)})")
        item = items[item_index - 1]
        mapping = item.GetSourceAudioChannelMapping() if hasattr(item, "GetSourceAudioChannelMapping") else None
        return _ok(track_index=track_index, item_index=item_index, mapping=_ser(mapping))

    else:
        return _err(
            f"Unknown action: {action}. Valid: get_audio_tracks, get_audio_items, "
            "get_volume, set_volume, set_mute, set_pan, fade_in, fade_out, "
            "get_voice_isolation, set_voice_isolation, get_audio_mapping"
        )


if __name__ == "__main__":
    mcp.run()
