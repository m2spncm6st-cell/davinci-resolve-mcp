# DaVinci Resolve MCP Server

## Projektbeschreibung
MCP-Server zur stabilen Steuerung von DaVinci Resolve über Claude Code.
Fokus auf Stabilität, Lazy Connection und Reconnect-Logik.

## Aktuelle Phase
**Phase 0: Setup & Umgebung** — abgeschlossen
**Phase 1: Minimaler Server** — abgeschlossen (v0.1.0)
**Phase 2: Kern-Tools** — abgeschlossen (v0.2.0)
**Phase 3: Erweiterte Tools** — abgeschlossen (v0.3.0)
**Phase 4: Stabilisierung & Polish** — als nächstes

## Umgebung
- macOS 26.4 (Tahoe), Apple Silicon
- DaVinci Resolve Studio 20.3.1
- Python 3.12.11 via pyenv (System hat 3.14 — inkompatibel!)
- pyenv local 3.12.11 im Projektordner
- Scripting API: vorhanden
- fusionscript.so: vorhanden

## Wichtige Pfade
- Projekt: `~/Projects/davinci-resolve-mcp`
- Resolve Scripting API: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting`
- fusionscript.so: `/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so`
- Scripting Modules: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules`

## Architektur-Entscheidungen
- **FastMCP** (offizielles Python MCP SDK) als Server-Framework
- **stdio-Transport** (lokal, kein Netzwerk)
- **Compound-Tools** mit `action`-Parameter (spart Context Window)
  - Pattern: `tool_name(action: str, params: Optional[Dict]) -> Dict`
  - Intern if/elif-Routing auf Resolve-API-Methoden
  - Docstring als Action-Katalog für LLM
- **Lazy Connection**: Server startet sofort, verbindet erst beim ersten Tool-Call
- **Reconnect-Logik**: Automatischer Health-Check + Reconnect
  - Health-Check via `GetProductName()` als günstiger Ping
  - 2s Check-Interval, Cache dazwischen
- **Navigation-Helpers** (aus samuelgursky-Analyse):
  - `_check()` → Verbindung + Projekt prüfen
  - `_get_mp()` → MediaPool navigieren
  - `_get_tl()` → aktive Timeline holen
  - Tupel-Rückgabe: `(obj1, obj2, error_or_none)`
- **Normalisierte Responses**: `_err(msg)` → `{"error": msg}`, `_ok(**kw)` → `{"success": True, ...}`
- **Serialisierungs-Helper**: `_ser(obj)` für Resolve-Objekte → JSON
- **Pydantic-Validierung** für alle Tool-Inputs

## Phasenplan
- [x] Phase 0: Setup & Umgebung
- [x] Phase 1: Minimaler Server (v0.1.0) — resolve_status, resolve_control, project Tool
- [x] Phase 2: Kern-Tools (v0.2.0) — timeline, media_pool, set_page
- [x] Phase 3: Erweiterte Tools (v0.3.0) — color, fusion, deliver, fairlight
- [ ] Phase 4: Stabilisierung & Polish

## Bekannte Probleme
- Python 3.13+ hat ABI-Inkompatibilitäten mit fusionscript.so → pyenv 3.12 verwenden
- Resolve muss laufen bevor Tools aufgerufen werden
- "External scripting using: Local" muss in Resolve-Einstellungen aktiv sein
- FastMCP v1.26: `description` Parameter heißt jetzt `instructions`

## Git-Workflow
- Conventional Commits auf Deutsch: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- Git-Tags bei Meilensteinen (v0.1.0, v0.2.0, etc.)

## Referenz-Repo Erkenntnisse (samuelgursky/davinci-resolve-mcp)
- 27 Compound-Tools im Standard-Mode, 342 granulare Tools alternativ
- Dreistufige Lazy-Connect: Cache → Single Connect → Auto-Launch + Poll (60s)
- Gestufte Navigation-Helpers als Middleware (`_check`, `_get_mp`, `_get_tl`)
- Sandbox-Path-Redirection für sichere Dateipfade
- Kein Health-Check mit Interval — einmal verbunden, dauerhaft gecacht

## Implementierte Tools (9 Tools, 50+ Actions)
- `resolve_status()` — Verbindungsstatus, Version, Projekt, Page
- `resolve_control(action, page)` — status, get_page, set_page, get_version
- `project(action, name)` — list, get_current, open, save, create, close
- `timeline(action, ...)` — list, get_current, set_current, create, get_tracks, get_items, get_markers, duplicate
- `media_pool(action, ...)` — list_folders, get/set_current_folder, create_folder, list_clips, import_media, create_timeline_from_clips, get_root_folder, selected_clips
- `color(action, ...)` — get_current_item, get_node_graph, get_nodes, get/set_lut, set_node_enabled, reset_grades, get_color_groups, get_timeline_nodes
- `deliver(action, ...)` — get_formats, get_codecs, get_presets, load_preset, get/set_current_format, set_render_settings, add/list/delete_jobs, get_job_status, start/stop_render, is_rendering
- `fusion(action, ...)` — list_comps, get/add/import/export/delete/rename_comp, insert_fusion_clip
- `fairlight(action, ...)` — get_audio_tracks, get_audio_items

## Offene TODOs
- [ ] Phase 4: Edge-Cases behandeln (Reconnect nach Resolve-Neustart)
- [ ] Phase 4: Alle Pages durchgehend E2E-testen
- [ ] MCP-Server in Claude Code tatsächlich nutzen (aus Projektordner starten)

## Letzte Änderung
2026-03-28 — Phase 3 abgeschlossen (v0.3.0): 9 Tools, 46/46 Live-Tests, 29/29 Unit-Tests
