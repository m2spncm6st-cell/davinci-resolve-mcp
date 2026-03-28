# Phase 6 — Audio/Fairlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Erweitere das `fairlight` Tool um 6 neue Actions für Audio-Kontrolle (Lautstärke, Mute, Pan, Fade).

**Architecture:** Erweiterung der bestehenden `fairlight()` Funktion in `server.py` um neue Parameter und Actions. Item-Level-Operationen (volume, pan, fades) nutzen `TimelineItem` API, Track-Level-Mute nutzt `tl.SetTrackEnabled`. Tests in `tests/test_tools.py` als Integration-Tests in `TestWithResolve`.

**Tech Stack:** Python 3.12.11 (pyenv), FastMCP v1.26, DaVinci Resolve Scripting API, pytest

---

## File Structure

| Datei | Änderung |
|-------|----------|
| `src/server.py` | `fairlight()` Signatur + 6 neue Actions + aktualisierter Error-String |
| `tests/test_tools.py` | 6 neue Tests in `TestFairlightWithResolve` Klasse |

---

### Task 1: Test für `get_volume` schreiben

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

Am Ende von `tests/test_tools.py` hinzufügen (nach `TestWithResolve`):

```python
class TestFairlightWithResolve:
    """Audio/Fairlight tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import fairlight
        self.fairlight = fairlight

    def test_get_volume_missing_params(self):
        """get_volume ohne item_index gibt Fehler zurück."""
        result = self.fairlight(action="get_volume", track_index=1)
        assert result["success"] is False
        assert "item_index" in result["error"]
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
cd ~/Projects/davinci-resolve-mcp
pytest tests/test_tools.py::TestFairlightWithResolve::test_get_volume_missing_params -v
```

Erwartet: `FAILED` — `fairlight` kennt `item_index` noch nicht.

---

### Task 2: `fairlight` Signatur + `get_volume` implementieren

**Files:**
- Modify: `src/server.py:1265`

- [ ] **Schritt 1: Signatur erweitern**

Ersetze die `fairlight`-Funktion-Signatur (Zeile ~1265):

```python
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
```

- [ ] **Schritt 2: Helper-Hilfsfunktion und `get_volume` Action hinzufügen**

Direkt vor dem `else:` am Ende der `fairlight`-Funktion (vor Zeile ~1309) einfügen:

```python
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
```

- [ ] **Schritt 3: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_get_volume_missing_params -v
```

Erwartet: `PASSED`

- [ ] **Schritt 4: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: fairlight — get_volume Action"
```

---

### Task 3: `set_volume` implementieren

**Files:**
- Modify: `src/server.py`, `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

In `TestFairlightWithResolve` hinzufügen:

```python
    def test_set_volume_missing_volume_param(self):
        """set_volume ohne volume-Parameter gibt Fehler zurück."""
        result = self.fairlight(action="set_volume", track_index=1, item_index=1)
        assert result["success"] is False
        assert "volume" in result["error"]
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_set_volume_missing_volume_param -v
```

Erwartet: `FAILED`

- [ ] **Schritt 3: `set_volume` Action hinzufügen**

In `server.py` nach dem `get_volume`-Block einfügen:

```python
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
```

- [ ] **Schritt 4: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_set_volume_missing_volume_param -v
```

Erwartet: `PASSED`

- [ ] **Schritt 5: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: fairlight — set_volume Action"
```

---

### Task 4: `set_mute` implementieren

**Files:**
- Modify: `src/server.py`, `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

In `TestFairlightWithResolve` hinzufügen:

```python
    def test_set_mute_missing_muted_param(self):
        """set_mute ohne muted-Parameter gibt Fehler zurück."""
        result = self.fairlight(action="set_mute", track_index=1)
        assert result["success"] is False
        assert "muted" in result["error"]
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_set_mute_missing_muted_param -v
```

Erwartet: `FAILED`

- [ ] **Schritt 3: `set_mute` Action hinzufügen**

In `server.py` nach dem `set_volume`-Block einfügen:

```python
    elif action == "set_mute":
        if track_index is None:
            return _err("'track_index' is required (1-based)")
        if muted is None:
            return _err("'muted' is required (true to mute, false to unmute)")
        if not hasattr(tl, "SetTrackEnabled"):
            return _err("SetTrackEnabled() not available in this Resolve version")
        result = tl.SetTrackEnabled("audio", track_index, not muted)
        return _ok(track_index=track_index, muted=muted, set=result)
```

- [ ] **Schritt 4: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_set_mute_missing_muted_param -v
```

Erwartet: `PASSED`

- [ ] **Schritt 5: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: fairlight — set_mute Action"
```

---

### Task 5: `set_pan` implementieren

**Files:**
- Modify: `src/server.py`, `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

In `TestFairlightWithResolve` hinzufügen:

```python
    def test_set_pan_out_of_range(self):
        """set_pan mit pan außerhalb -1.0..1.0 gibt Fehler zurück."""
        result = self.fairlight(action="set_pan", track_index=1, item_index=1, pan=2.5)
        assert result["success"] is False
        assert "1.0" in result["error"]
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_set_pan_out_of_range -v
```

Erwartet: `FAILED`

- [ ] **Schritt 3: `set_pan` Action hinzufügen**

In `server.py` nach dem `set_mute`-Block einfügen:

```python
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
```

- [ ] **Schritt 4: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_set_pan_out_of_range -v
```

Erwartet: `PASSED`

- [ ] **Schritt 5: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: fairlight — set_pan Action"
```

---

### Task 6: `fade_in` und `fade_out` implementieren

**Files:**
- Modify: `src/server.py`, `tests/test_tools.py`

- [ ] **Schritt 1: Tests schreiben**

In `TestFairlightWithResolve` hinzufügen:

```python
    def test_fade_in_missing_duration(self):
        """fade_in ohne duration gibt Fehler zurück."""
        result = self.fairlight(action="fade_in", track_index=1, item_index=1)
        assert result["success"] is False
        assert "duration" in result["error"]

    def test_fade_out_missing_duration(self):
        """fade_out ohne duration gibt Fehler zurück."""
        result = self.fairlight(action="fade_out", track_index=1, item_index=1)
        assert result["success"] is False
        assert "duration" in result["error"]
```

- [ ] **Schritt 2: Tests ausführen — erwartet FAIL**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_fade_in_missing_duration tests/test_tools.py::TestFairlightWithResolve::test_fade_out_missing_duration -v
```

Erwartet: beide `FAILED`

- [ ] **Schritt 3: `fade_in` und `fade_out` Actions hinzufügen**

In `server.py` nach dem `set_pan`-Block, vor dem abschließenden `else:` einfügen:

```python
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
        result = item.SetProperty("FadeOutDuration", duration)
        return _ok(track_index=track_index, item_index=item_index, duration=duration, set=result)
```

- [ ] **Schritt 4: Fehler-String am Ende der `fairlight`-Funktion aktualisieren**

Den abschließenden `_err` in `fairlight()` ersetzen:

```python
    else:
        return _err(
            f"Unknown action: {action}. Valid: get_audio_tracks, get_audio_items, "
            "get_volume, set_volume, set_mute, set_pan, fade_in, fade_out"
        )
```

- [ ] **Schritt 5: Tests ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestFairlightWithResolve::test_fade_in_missing_duration tests/test_tools.py::TestFairlightWithResolve::test_fade_out_missing_duration -v
```

Erwartet: beide `PASSED`

- [ ] **Schritt 6: Alle Tests ausführen — alle müssen grün sein**

```bash
pytest tests/ -v
```

Erwartet: `35 passed` (29 bestehend + 6 neue)

- [ ] **Schritt 7: Commit + Tag**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: fairlight — fade_in und fade_out Actions"
git tag v1.2.0
git push && git push --tags
```

---

## CLAUDE.md aktualisieren

- [ ] **Schritt 1: `fairlight` Eintrag in CLAUDE.md aktualisieren**

In `CLAUDE.md` den `fairlight`-Abschnitt unter "Implementierte Tools" ersetzen:

```markdown
### fairlight(action, track_index, item_index, volume, muted, pan, duration)
get_audio_tracks, get_audio_items,
get_volume, set_volume, set_mute, set_pan, fade_in, fade_out
```

Außerdem die Zähler aktualisieren:
```markdown
## Implementierte Tools (10 Tools, 81+ Actions)
```

Und unter Phasenplan:
```markdown
- [x] Phase 6: Audio/Fairlight (v1.2.0)
```

- [ ] **Schritt 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md für v1.2.0 aktualisiert"
```
