# Phase 7 — Transitions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Neues `transition` Tool mit 4 Actions zum Hinzufügen, Entfernen, Lesen und Auflisten von Übergängen zwischen Clips.

**Architecture:** Neues `@mcp.tool()` `transition()` in `server.py`, registriert nach `fusion`. Nutzt `TimelineItem.AddTransition()` für das Einfügen, `GetItemListInTrack` für den Item-Zugriff. `list_types` gibt hardcodierte Standardtypen zurück (Resolve API kennt keine dynamische Liste). Tests in `tests/test_tools.py` als `TestTransitionWithResolve` Klasse.

**Tech Stack:** Python 3.12.11 (pyenv), FastMCP v1.26, DaVinci Resolve Scripting API, pytest

---

## File Structure

| Datei | Änderung |
|-------|----------|
| `src/server.py` | Neues `transition()` Tool nach `fusion()` (vor `fairlight`) |
| `tests/test_tools.py` | 4 neue Tests in `TestTransitionWithResolve` Klasse |

---

### Task 1: Test für `list_types` schreiben

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

Am Ende von `tests/test_tools.py` hinzufügen:

```python
class TestTransitionWithResolve:
    """Transition tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import transition
        self.transition = transition

    def test_list_types_returns_known_types(self):
        """list_types gibt eine Liste bekannter Transition-Typen zurück."""
        result = self.transition(action="list_types")
        assert result["success"] is True
        assert "types" in result
        assert "Dissolve" in result["types"]
        assert "Cut" in result["types"]
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
cd ~/Projects/davinci-resolve-mcp
pytest tests/test_tools.py::TestTransitionWithResolve::test_list_types_returns_known_types -v
```

Erwartet: `FAILED` — `transition` existiert noch nicht.

---

### Task 2: `transition` Tool mit `list_types` implementieren

**Files:**
- Modify: `src/server.py`

- [ ] **Schritt 1: `transition` Tool in `server.py` hinzufügen**

Nach dem `fusion`-Tool (nach Zeile ~1258, vor dem `fairlight`-Block) einfügen:

```python
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
```

- [ ] **Schritt 2: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestTransitionWithResolve::test_list_types_returns_known_types -v
```

Erwartet: `PASSED`

- [ ] **Schritt 3: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: transition Tool — list_types Action"
```

---

### Task 3: Tests für `get`, `add`, `remove` schreiben und ausführen

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Schritt 1: Tests schreiben**

In `TestTransitionWithResolve` hinzufügen:

```python
    def test_add_missing_transition_type(self):
        """add ohne transition_type gibt Fehler zurück."""
        result = self.transition(
            action="add", track_type="video", track_index=1, item_index=1, duration=24
        )
        assert result["success"] is False
        assert "transition_type" in result["error"]

    def test_add_invalid_transition_type(self):
        """add mit unbekanntem transition_type gibt Fehler zurück."""
        result = self.transition(
            action="add", track_type="video", track_index=1, item_index=1,
            transition_type="UnknownFX", duration=24
        )
        assert result["success"] is False
        assert "UnknownFX" in result["error"]

    def test_add_missing_duration(self):
        """add ohne duration gibt Fehler zurück."""
        result = self.transition(
            action="add", track_type="video", track_index=1, item_index=1,
            transition_type="Dissolve"
        )
        assert result["success"] is False
        assert "duration" in result["error"]
```

- [ ] **Schritt 2: Tests ausführen — erwartet PASS** (Validierungsfehler schlägt vor Item-Lookup an)

```bash
pytest tests/test_tools.py::TestTransitionWithResolve -v
```

Erwartet: alle 4 Tests `PASSED`

- [ ] **Schritt 3: Alle Tests ausführen — alle müssen grün sein**

```bash
pytest tests/ -v
```

Erwartet: `39 passed` (29 bestehend + 6 aus Phase 6 + 4 Transition-Tests)

> Hinweis: Falls Phase 6 noch nicht abgeschlossen ist, erwartet: `33 passed` (29 + 4 neue).

- [ ] **Schritt 4: Commit + Tag**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: transition Tool — get, add, remove Actions mit Tests"
git tag v1.3.0
git push && git push --tags
```

---

## CLAUDE.md aktualisieren

- [ ] **Schritt 1: `transition` Tool in CLAUDE.md eintragen**

In `CLAUDE.md` nach dem `fairlight`-Eintrag hinzufügen:

```markdown
### transition(action, track_type, track_index, item_index, transition_type, duration)
list_types, get, add, remove
```

Zähler aktualisieren:
```markdown
## Implementierte Tools (11 Tools, 85+ Actions)
```

Und unter Phasenplan:
```markdown
- [x] Phase 7: Transitions (v1.3.0)
```

- [ ] **Schritt 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md für v1.3.0 aktualisiert"
```
