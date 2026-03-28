# DaVinci Resolve MCP Server

## Projektbeschreibung
MCP-Server zur stabilen Steuerung von DaVinci Resolve über Claude Code.
Fokus auf Stabilität, Lazy Connection und Reconnect-Logik.

## Status: v1.5.0 — Full Stack API-Erweiterung
Alle Phasen abgeschlossen. Server ist produktionsreif.

## Umgebung
- macOS 26.4 (Tahoe), Apple Silicon
- DaVinci Resolve Studio 20.3.1
- Python 3.12.11 via pyenv (System hat 3.14 — inkompatibel!)
- pyenv local 3.12.11 im Projektordner
- Scripting API + fusionscript.so vorhanden

## Wichtige Pfade
- Projekt: `~/Projects/davinci-resolve-mcp`
- Resolve Scripting API: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting`
- fusionscript.so: `/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so`
- Scripting Modules: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules`

## MCP-Registrierung
```bash
cd ~/Projects/davinci-resolve-mcp
claude mcp add davinci-resolve --scope project \
  -e PYTHONPATH="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules" \
  -- /Users/Alex/.pyenv/versions/3.12.11/bin/python3 src/server.py
```

## Architektur
- **FastMCP v1.26** mit `instructions`-Parameter (nicht `description`)
- **stdio-Transport** (lokal)
- **Compound-Tools**: `tool_name(action: str, ...)` → wenige Tools, viele Actions
- **Lazy Connection**: Erst beim ersten Tool-Call verbinden
- **Reconnect mit Retry**: 3 Versuche, Health-Check via `GetProductName()`, 2s Cache
- **safe_tool Decorator**: Alle Tools gegen Crashes abgesichert
- **Navigation-Helpers**: `check()`, `get_media_pool()`, `get_timeline()` mit Tupel-Rückgabe
- **Normalisierte Responses**: `_err(msg)`, `_ok(**kw)`, `_ser(obj)`

## Implementierte Tools (11 Tools, 111+ Actions)

### resolve_status()
Verbindungsstatus, Version, Projekt, Page

### resolve_control(action, page)
status, get_page, set_page, get_version

### project(action, name)
list, get_current, open, save, create, close

### timeline(action, name, index, track_type, track_index, export_format, file_path)
list, get_current, set_current, create, get_tracks, get_items, get_markers,
add_marker, delete_markers, get_settings, duplicate,
add_track, delete_track, export, insert_title, insert_generator, delete_clips,
get_marker_clips, split_at_markers, delete_between_markers, rename_clips_from_markers,
get_timecode, set_timecode

### timeline_item(action, track_type, track_index, item_index, property_name, property_value, clip_color, take_index, media_pool_clip, start_frame, end_frame, cache_type)
get_current, get_properties, set_property, get_info, set_clip_color,
clear_clip_color, set_enabled, get_source_info,
get_takes, get_selected_take, add_take, select_take, delete_take, finalize_take,
get_cache, set_cache, update_sidecar, stabilize

### media_pool(action, folder_name, file_paths, timeline_name)
list_folders, get_current_folder, set_current_folder, create_folder, delete_folder,
list_clips, get_clip_info, import_media, create_timeline_from_clips, get_root_folder,
selected_clips, append_to_timeline

### color(action, node_index, lut_path, item_index, version_name, version_type)
get_current_item, get_node_graph, get_nodes, get_lut, set_lut,
set_node_enabled, reset_grades, get_color_groups, get_timeline_nodes,
list_versions, get_version, add_version, load_version, delete_version,
create_magic_mask, regenerate_magic_mask, export_lut

### deliver(action, preset_name, target_dir, file_name, render_format, render_codec, job_id)
get_formats, get_codecs, get_presets, load_preset, get_current_format, set_format,
set_render_settings, add_job, list_jobs, get_job_status, start_render, stop_render,
is_rendering, delete_all_jobs

### fusion(action, comp_name, comp_index, file_path, new_name)
list_comps, get_comp, add_comp, import_comp, export_comp, delete_comp,
rename_comp, insert_fusion_clip

### fairlight(action, track_index, item_index, volume, muted, pan, duration, enabled, amount)
get_audio_tracks, get_audio_items,
get_volume, set_volume, set_mute, set_pan, fade_in, fade_out,
get_voice_isolation, set_voice_isolation, get_audio_mapping

### transition(action, track_type, track_index, item_index, transition_type, duration)
list_types, get, add, remove

## Phasenplan
- [x] Phase 0: Setup & Umgebung
- [x] Phase 1: Minimaler Server (v0.1.0)
- [x] Phase 2: Kern-Tools (v0.2.0)
- [x] Phase 3: Erweiterte Tools (v0.3.0)
- [x] Phase 4: Stabilisierung & Polish (v1.0.0)
- [x] Phase 5: Editing-Capabilities (v1.1.0)
- [x] Phase 6: Audio/Fairlight (v1.2.0)
- [x] Phase 7: Transitions (v1.3.0)
- [x] Phase 8: Marker-basiertes Editing (v1.4.0)
- [x] Phase 9: Full Stack API-Erweiterung (v1.5.0)

## Bekannte Probleme
- Python 3.13+ inkompatibel mit fusionscript.so → pyenv 3.12 verwenden
- Resolve muss laufen bevor Tools aufgerufen werden
- "External scripting using: Local" muss in Resolve-Einstellungen aktiv sein
- FastMCP v1.26: `description` heißt `instructions`
- `.mcp.json` allein reicht nicht — `claude mcp add` für erste Registrierung nötig

## Git-Workflow
- Conventional Commits auf Deutsch
- Git-Tags bei Meilensteinen

## Letzte Änderung
2026-03-28 — v1.5.0: Full Stack API-Erweiterung (Playhead, Takes, Cache, Versions, Magic Mask, LUT Export, Voice Isolation, Audio Mapping)
