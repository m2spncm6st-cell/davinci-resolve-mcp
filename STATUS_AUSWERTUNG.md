# DaVinci Resolve MCP Server — Projektauswertung
**Stand: April 2026 · Version 2.0.0**

---

## Was ist das Projekt?

Ein **MCP-Server** (Model Context Protocol), der DaVinci Resolve Studio über Claude Code steuerbar macht. Claude kann damit Schnitt, Color Grading, Audio, Rendering und Fusion-Effekte direkt per Sprache auslösen — ohne manuelle UI-Interaktion in Resolve.

---

## Aktueller Status: Produktionsreif ✓

| Kennzahl | Wert |
|---|---|
| Version | v2.0.0 |
| Codezeilen | ~4.750 (Python) |
| MCP-Tools | 13 |
| Actions gesamt | 127 |
| Automatisierte Tests | 100 |
| Offene Bugs | 0 |
| Phasen abgeschlossen | 14 / 14 |

---

## Was funktioniert

### 13 Tools mit 127 Actions

| Tool | Beschreibung | Beispiel-Actions |
|---|---|---|
| `resolve_control` | Verbindung & Navigation | status, set_page, get_version |
| `project` | Projekte verwalten | list, open, save, create, get_settings |
| `timeline` | Schnitt & Marker | create, get_items, add_marker, split_at_markers, export |
| `timeline_item` | Clip-Eigenschaften | trim, set_speed, set_cdl, copy_grades, stabilize |
| `media_pool` | Medien importieren | import_media, append_to_timeline, create_timeline_from_clips |
| `color` | Color Grading | get_nodes, set_lut, auto_grade, grab_and_analyze, export_lut |
| `deliver` | Render & Export | set_format, add_job, start_render, get_job_status |
| `fusion` | Fusion Compositions | list_comps, import_comp, insert_fusion_clip |
| `fairlight` | Audio-Editing | set_volume, fade_in/out, set_pan, voice_isolation |
| `transition` | Übergänge | list_types, add, remove |
| `fx` | Cinematic Effects | apply_look (12 CDL-Presets), add_transition (6 Templates), create_3d_text |
| `analyze_media` | KI-Analyse | scenes, brightness, full |
| `transition` | Timeline-Übergänge | list_types, get, add, remove |

### Architektur-Highlights

- **Lazy Connection** — Server startet sofort; Resolve-Verbindung erst beim ersten Tool-Call
- **Auto-Reconnect** — 3 Versuche mit Health-Check-Cache (2 s) bei Resolve-Neustart
- **`safe_tool` Decorator** — Alle Tools gegen Crashes abgesichert, keine Server-Abstürze
- **Structured Logging** — `~/.resolve-mcp.log` mit Timestamps
- **PID-Guard** — Verhindert doppelte Server-Instanzen (`~/.resolve-mcp.pid`)
- **Portabel** — `ffmpeg`-Pfade via `shutil.which()`, kein Hardcoding

### Testabdeckung

| Testdatei | Tests | Abdeckt |
|---|---|---|
| `test_connection.py` | 9 | Verbindungslogik, Serialisierung, Helpers |
| `test_tools.py` | 63 | Response-Formate, Tool-Dispatcher |
| `test_fx.py` | 20 | FX-Tool: CDL-Presets, Transitions, 3D-Text |
| `test_stability.py` | 8 | Reconnect-Mechanik, Cache |
| **Gesamt** | **100** | |

---

## Bekannte Limitierungen (keine Bugs — API-Grenzen von Resolve 20.3)

| Problem | Ursache | Workaround |
|---|---|---|
| Transitions per API nicht setzbar | `AddTransitionByName()` = NoneType | Template-basierte Fusion Transitions via `fx add_transition` |
| `SplitClip()` nicht verfügbar | Resolve 20.3 API-Lücke | `append_to_timeline` mit In/Out-Points |
| Neue LUTs erst nach Neustart sichtbar | Resolve-internes Index-Caching | Bestehende `.cube`-Datei überschreiben |
| Solid Color Generator Farbe nicht setzbar | `GetFusionCompByIndex()` = None | `ffmpeg`-generierte schwarze MP4 als Ersatz |
| `AddMarker` schlägt bei leerem Namen fehl | Resolve-Anforderung | Immer non-empty `name` übergeben |
| Python 3.13+ inkompatibel | `fusionscript.so`-Bindung | pyenv 3.12.11 als feste Version |

---

## Entwicklungsverlauf (14 Phasen)

```
Phase 0–1  Setup, Umgebung, minimaler Server
Phase 2–3  Kern-Tools: Timeline, MediaPool, Color, Deliver
Phase 4    Stabilisierung: Reconnect, safe_tool, Fehlerbehandlung
Phase 5    Editing: Trim, Multi-Clip-Append, Marker-Workflow
Phase 6    Audio/Fairlight: Volume, Pan, Fades, Voice Isolation
Phase 7    Transitions: list, add, remove
Phase 8    Marker-basiertes Editing: split/delete/rename at markers
Phase 9    Full-Stack API-Erweiterung: Takes, CDL, Smart Reframe
Phase 10   Color Grading: Magic Mask, LUT-Export, Auto-Grade
Phase 11   Cinematic FPV Workflow: D-Log M → Rec.709
Phase 12   Sizilien-Video: fehlende API-Lücken geschlossen
Phase 13   Timeline Trim, Global MCP, Multi-Clip-Append
Phase 14   v2.0.0: Code-Review Cleanup, Logging, Portabilität ✓
```

---

## Umgebung

- **macOS** 26.4 (Tahoe), Apple Silicon
- **DaVinci Resolve Studio** 20.3.1
- **Python** 3.12.11 via pyenv (System 3.14 inkompatibel)
- **FastMCP** v1.26
- **Transport:** stdio (lokal)
- **MCP-Scope:** user-global (funktioniert in jedem Verzeichnis)

---

## Setup (Kurzform)

```bash
# 1. Python-Version sicherstellen
pyenv local 3.12.11
pip install -r requirements.txt

# 2. MCP registrieren
claude mcp add davinci-resolve --scope user \
  -e PYTHONPATH="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules" \
  -- /Users/Alex/.pyenv/versions/3.12.11/bin/python3 src/server.py

# 3. Resolve starten, "External scripting: Local" aktivieren
# 4. Claude Code öffnen → Tools sofort verfügbar
```

---

*Erstellt: 2026-04-21 — Alexander Dreger*
