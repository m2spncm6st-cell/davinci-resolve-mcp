# Phase 8 — Marker-basiertes Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Erweitere das `timeline` Tool um 4 neue Actions, die Marker als Schnittmarken nutzen — Clips abrufen, aufsplitten, löschen und umbenennen basierend auf Marker-Positionen.

**Architecture:** Erweiterung der bestehenden `timeline()` Funktion in `server.py`. Alle neuen Actions bauen auf bereits implementierten API-Calls auf: `GetMarkers()`, `GetItemListInTrack()`, `DeleteClips()`, `SplitClip()`, `SetClipProperty()`. `split_at_markers` ist die komplexeste Action — fehlerresistent per try/except pro Split. Tests in `tests/test_tools.py` als `TestMarkerEditingWithResolve` Klasse.

**Tech Stack:** Python 3.12.11 (pyenv), FastMCP v1.26, DaVinci Resolve Scripting API, pytest

---

## File Structure

| Datei | Änderung |
|-------|----------|
| `src/server.py` | 4 neue Actions in `timeline()` + aktualisierter Error-String |
| `tests/test_tools.py` | 4 neue Tests in `TestMarkerEditingWithResolve` Klasse |

---

### Task 1: Test für `get_marker_clips` schreiben

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

Am Ende von `tests/test_tools.py` hinzufügen:

```python
class TestMarkerEditingWithResolve:
    """Marker-based editing tests that only run when Resolve is available."""

    def setup_method(self):
        if not _resolve_available():
            import pytest
            pytest.skip("DaVinci Resolve not running")
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.server import timeline
        self.timeline = timeline

    def test_get_marker_clips_returns_list(self):
        """get_marker_clips gibt success=True und eine clips-Liste zurück."""
        result = self.timeline(action="get_marker_clips")
        assert result["success"] is True
        assert "clips" in result
        assert isinstance(result["clips"], list)
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
cd ~/Projects/davinci-resolve-mcp
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_get_marker_clips_returns_list -v
```

Erwartet: `FAILED` — `get_marker_clips` ist noch nicht implementiert.

---

### Task 2: `get_marker_clips` implementieren

**Files:**
- Modify: `src/server.py`

- [ ] **Schritt 1: Action in `timeline()` hinzufügen**

In `server.py` direkt vor dem abschließenden `else:` der `timeline()`-Funktion (vor Zeile ~444) einfügen:

```python
    elif action == "get_marker_clips":
        if err:
            return err
        markers = tl.GetMarkers()
        if not markers:
            return _ok(clips=[], marker_count=0)
        color_filter = name  # name-Parameter als optionaler Farbfilter
        matched = []
        video_count = tl.GetTrackCount("video")
        for frame, marker_data in markers.items():
            if color_filter and marker_data.get("color") != color_filter:
                continue
            for track_i in range(1, video_count + 1):
                items = tl.GetItemListInTrack("video", track_i)
                if not items:
                    continue
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
```

- [ ] **Schritt 2: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_get_marker_clips_returns_list -v
```

Erwartet: `PASSED`

- [ ] **Schritt 3: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: timeline — get_marker_clips Action"
```

---

### Task 3: `split_at_markers` implementieren

**Files:**
- Modify: `src/server.py`, `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

In `TestMarkerEditingWithResolve` hinzufügen:

```python
    def test_split_at_markers_returns_summary(self):
        """split_at_markers gibt Anzahl erfolgreicher und fehlgeschlagener Splits zurück."""
        result = self.timeline(action="split_at_markers")
        assert result["success"] is True
        assert "splits_attempted" in result
        assert "splits_succeeded" in result
        assert "splits_failed" in result
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_split_at_markers_returns_summary -v
```

Erwartet: `FAILED`

- [ ] **Schritt 3: `split_at_markers` Action hinzufügen**

In `server.py` nach dem `get_marker_clips`-Block einfügen:

```python
    elif action == "split_at_markers":
        if err:
            return err
        markers = tl.GetMarkers()
        if not markers:
            return _ok(splits_attempted=0, splits_succeeded=0, splits_failed=0, message="No markers found")
        color_filter = name
        attempted = 0
        succeeded = 0
        failed = 0
        errors = []
        video_count = tl.GetTrackCount("video")
        for frame, marker_data in sorted(markers.items()):
            if color_filter and marker_data.get("color") != color_filter:
                continue
            attempted += 1
            split_ok = False
            for track_i in range(1, video_count + 1):
                items = tl.GetItemListInTrack("video", track_i)
                if not items:
                    continue
                for item in items:
                    if item.GetStart() < frame < item.GetEnd():
                        try:
                            if hasattr(tl, "SplitClip"):
                                result_split = tl.SplitClip(item, frame)
                                if result_split:
                                    split_ok = True
                            else:
                                errors.append(f"Frame {frame}: SplitClip() not available")
                        except Exception as e:
                            errors.append(f"Frame {frame}: {e}")
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
```

- [ ] **Schritt 4: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_split_at_markers_returns_summary -v
```

Erwartet: `PASSED`

- [ ] **Schritt 5: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: timeline — split_at_markers Action"
```

---

### Task 4: `delete_between_markers` implementieren

**Files:**
- Modify: `src/server.py`, `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

In `TestMarkerEditingWithResolve` hinzufügen:

```python
    def test_delete_between_markers_missing_params(self):
        """delete_between_markers ohne marker_a_frame gibt Fehler zurück."""
        result = self.timeline(action="delete_between_markers")
        assert result["success"] is False
        assert "marker_a_frame" in result["error"]
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_delete_between_markers_missing_params -v
```

Erwartet: `FAILED`

- [ ] **Schritt 3: `delete_between_markers` Action hinzufügen**

In `server.py` nach dem `split_at_markers`-Block einfügen:

```python
    elif action == "delete_between_markers":
        if err:
            return err
        # track_index wird hier als marker_a_frame verwendet (erster Marker-Frame)
        # export_format wird als marker_b_frame verwendet (zweiter Marker-Frame)
        # Hinweis: Wir nutzen zwei bestehende int-Parameter um neue Felder zu vermeiden
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
```

- [ ] **Schritt 4: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_delete_between_markers_missing_params -v
```

Erwartet: `PASSED`

- [ ] **Schritt 5: Commit**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: timeline — delete_between_markers Action"
```

---

### Task 5: `rename_clips_from_markers` implementieren + Fehler-String + Abschluss

**Files:**
- Modify: `src/server.py`, `tests/test_tools.py`

- [ ] **Schritt 1: Test schreiben**

In `TestMarkerEditingWithResolve` hinzufügen:

```python
    def test_rename_clips_from_markers_returns_summary(self):
        """rename_clips_from_markers gibt Anzahl umbenannter Clips zurück."""
        result = self.timeline(action="rename_clips_from_markers")
        assert result["success"] is True
        assert "renamed" in result
        assert isinstance(result["renamed"], int)
```

- [ ] **Schritt 2: Test ausführen — erwartet FAIL**

```bash
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_rename_clips_from_markers_returns_summary -v
```

Erwartet: `FAILED`

- [ ] **Schritt 3: `rename_clips_from_markers` Action hinzufügen**

In `server.py` nach dem `delete_between_markers`-Block, vor dem abschließenden `else:` einfügen:

```python
    elif action == "rename_clips_from_markers":
        if err:
            return err
        markers = tl.GetMarkers()
        if not markers:
            return _ok(renamed=0, message="No markers found")
        color_filter = name
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
                for frame, marker_data in markers.items():
                    if color_filter and marker_data.get("color") != color_filter:
                        continue
                    if clip_start <= frame < clip_end:
                        dist = abs(frame - clip_start)
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            best_frame = frame
                            best_marker = marker_data
                if best_frame is not None and best_marker.get("name"):
                    item.SetClipProperty("Clip Name", best_marker["name"])
                    renamed += 1
        return _ok(renamed=renamed)
```

- [ ] **Schritt 4: Fehler-String in `timeline()` aktualisieren**

Den abschließenden `_err` in `timeline()` ersetzen:

```python
    else:
        return _err(
            f"Unknown action: {action}. Valid: list, get_current, set_current, create, "
            "get_tracks, get_items, get_markers, add_marker, delete_markers, get_settings, "
            "duplicate, add_track, delete_track, export, insert_title, insert_generator, "
            "delete_clips, get_marker_clips, split_at_markers, delete_between_markers, "
            "rename_clips_from_markers"
        )
```

- [ ] **Schritt 5: Test ausführen — erwartet PASS**

```bash
pytest tests/test_tools.py::TestMarkerEditingWithResolve::test_rename_clips_from_markers_returns_summary -v
```

Erwartet: `PASSED`

- [ ] **Schritt 6: Alle Tests ausführen — alle müssen grün sein**

```bash
pytest tests/ -v
```

Erwartet (nach allen drei Phasen): `43 passed` (29 bestehend + 6 Phase 6 + 4 Phase 7 + 4 Phase 8)

- [ ] **Schritt 7: Commit + Tag**

```bash
git add src/server.py tests/test_tools.py
git commit -m "feat: timeline — rename_clips_from_markers Action"
git tag v1.4.0
git push && git push --tags
```

---

## CLAUDE.md aktualisieren

- [ ] **Schritt 1: `timeline` Eintrag und Zähler in CLAUDE.md aktualisieren**

In `CLAUDE.md` den `timeline`-Eintrag erweitern:

```markdown
### timeline(action, name, index, track_type, track_index, export_format, file_path)
list, get_current, set_current, create, get_tracks, get_items, get_markers,
add_marker, delete_markers, get_settings, duplicate,
add_track, delete_track, export, insert_title, insert_generator, delete_clips,
get_marker_clips, split_at_markers, delete_between_markers, rename_clips_from_markers
```

Zähler aktualisieren:
```markdown
## Implementierte Tools (11 Tools, 89+ Actions)
```

Unter Phasenplan hinzufügen:
```markdown
- [x] Phase 8: Marker-basiertes Editing (v1.4.0)
```

Letzte Änderung aktualisieren:
```markdown
## Letzte Änderung
2026-03-28 — v1.4.0: Marker-basiertes Editing (get_marker_clips, split_at_markers, delete_between_markers, rename_clips_from_markers)
```

- [ ] **Schritt 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md für v1.4.0 aktualisiert"
```

---

## Hinweis: `delete_between_markers` Parameter-Mapping

Da `timeline()` keine dedizierten `marker_a_frame`/`marker_b_frame` Parameter hat und die Signatur nicht gebrochen werden soll, nutzt `delete_between_markers` die bestehenden Integer-Parameter:
- `track_index` → `marker_a_frame` (Start-Frame)
- `index` → `marker_b_frame` (End-Frame)

Das ist in der Docstring-Dokumentation der Action explizit beschrieben. Falls die Signatur in einer späteren Phase erweitert wird, können dedizierte Parameter hinzugefügt werden.
