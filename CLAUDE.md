# DaVinci Resolve MCP Server

## Projektbeschreibung
MCP-Server zur stabilen Steuerung von DaVinci Resolve über Claude Code.
Fokus auf Stabilität, Lazy Connection und Reconnect-Logik.

## Aktuelle Phase
**Phase 0: Setup & Umgebung** — abgeschlossen
**Phase 1: Minimaler Server** — als nächstes

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
- [ ] Phase 1: Minimaler Server (resolve_status Tool, MCP-Registrierung)
- [ ] Phase 2: Kern-Tools (project, timeline, media_pool)
- [ ] Phase 3: Erweiterte Tools (color, fusion, deliver)
- [ ] Phase 4: Stabilisierung & Polish

## Bekannte Probleme
- Python 3.13+ hat ABI-Inkompatibilitäten mit fusionscript.so → pyenv 3.12 verwenden
- Resolve muss laufen bevor Tools aufgerufen werden
- "External scripting using: Local" muss in Resolve-Einstellungen aktiv sein

## Git-Workflow
- Conventional Commits auf Deutsch: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- Git-Tags bei Meilensteinen (v0.1.0, v0.2.0, etc.)

## Referenz-Repo Erkenntnisse (samuelgursky/davinci-resolve-mcp)
- 27 Compound-Tools im Standard-Mode, 342 granulare Tools alternativ
- Dreistufige Lazy-Connect: Cache → Single Connect → Auto-Launch + Poll (60s)
- Gestufte Navigation-Helpers als Middleware (`_check`, `_get_mp`, `_get_tl`)
- Sandbox-Path-Redirection für sichere Dateipfade
- Kein Health-Check mit Interval — einmal verbunden, dauerhaft gecacht

## Offene TODOs
- [ ] Phase 1: resolve_status Tool testen mit laufendem Resolve
- [ ] Dependencies installieren (pip install -r requirements.txt)
- [ ] MCP in Claude Code registrieren
- [ ] Navigation-Helpers implementieren (_check, _get_mp, _get_tl)
- [ ] Compound-Tool Pattern auf project-Tool anwenden

## Letzte Änderung
2026-03-28 — Phase 0 komplett: Struktur, pyenv 3.12, API-Doku, Referenz-Analyse
