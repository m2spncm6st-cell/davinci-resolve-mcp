# Sizilien Erinnerungsvideo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cinematische Timeline "Sizilien_Erinnerung" in DaVinci Resolve mit 8 DJI-Clips, 6 iPhone-Stills, Texttiteln, LUT + Auto-Grade vollständig aufbauen.

**Architecture:** Alle Schritte laufen über den DaVinci Resolve MCP-Server (`resolve_status`, `media_pool`, `timeline`, `timeline_item`, `color`). Kein Python-Skript wird geschrieben — nur MCP-Tool-Calls in Sequenz. SlowMo-Momente werden durch `timeline_item(action="set_property", property_name="Speed", property_value="25")` nach dem Platzieren gesetzt.

**Tech Stack:** DaVinci Resolve Studio 20.3.1, MCP v1.7.0, Python 3.12.11 (pyenv), ffprobe `/Users/Alex/.local/bin/ffprobe`

---

## Vorbereitung

**Quellordner:** `/Users/Alex/Projects/Video Projekt ätna sizilen ` *(trailing space)*
**iPhone-Ordner:** `/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone`
**LUT:** Indexierte `DJI_X7_DLOG2Rec709.cube` in `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/`

---

## Task 1: Verbindung prüfen und Projekt öffnen

**Files:** Keine Dateiänderungen — nur MCP-Calls.

- [ ] **Schritt 1.1: MCP-Prozess prüfen**

  Falls stale Prozess läuft:
  ```bash
  kill $(pgrep -f "davinci-resolve-mcp/src/server.py")
  ```

- [ ] **Schritt 1.2: resolve_status() aufrufen**

  ```
  resolve_status()
  ```
  Erwartet: `connected: true`, Projekt "Sizilien 25" offen, Resolve läuft.

- [ ] **Schritt 1.3: Resolve auf Edit-Seite setzen**

  ```
  resolve_control(action="set_page", page="edit")
  ```

---

## Task 2: Timeline erstellen (4K, 25fps)

- [ ] **Schritt 2.1: Neue leere Timeline anlegen**

  ```
  timeline(action="create", name="Sizilien_Erinnerung")
  ```
  Erwartet: `timeline: "Sizilien_Erinnerung"`

- [ ] **Schritt 2.2: Timeline als aktiv setzen**

  ```
  timeline(action="set_current", index=1)
  ```
  *(Index kann variieren — vorher `timeline(action="list")` aufrufen um den richtigen Index zu finden)*

- [ ] **Schritt 2.3: Timeline-Einstellungen manuell in Resolve setzen**

  Da `SetSetting` nicht im MCP verfügbar: In Resolve manuell über
  **Timeline → Timeline Settings**:
  - Resolution: 3840 × 2160
  - Frame Rate: 25fps
  - Color Science: DaVinci YRGB
  - Color Space: Rec.709 Gamma 2.4

---

## Task 3: Clips in Media Pool importieren

- [ ] **Schritt 3.1: Ordner "Sizilien_DJI" im Media Pool anlegen**

  ```
  media_pool(action="create_folder", folder_name="Sizilien_DJI")
  media_pool(action="set_current_folder", folder_name="Sizilien_DJI")
  ```

- [ ] **Schritt 3.2: Alle DJI-Clips importieren**

  ```
  media_pool(action="import_media", file_paths=[
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0934_joined_stabilized.mp4",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0936_stabilized_1.mp4",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0937_stabilized_1.mp4",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0938_stabilized_1.mp4",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0940_stabilized.mp4",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0942_stabilized.mp4",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0943_stabilized.mp4",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /DJI_0947_stabilized.mp4"
  ])
  ```
  Erwartet: 8 Clips importiert.

- [ ] **Schritt 3.3: Ordner "Sizilien_iPhone" anlegen und iPhone-Stills importieren**

  ```
  media_pool(action="create_folder", folder_name="Sizilien_iPhone")
  media_pool(action="set_current_folder", folder_name="Sizilien_iPhone")
  ```

  ```
  media_pool(action="import_media", file_paths=[
    "/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone/IMG_7159.heic",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone/IMG_1302.JPG",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone/IMG_7177.heic",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone/IMG_7187.HEIC",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone/IMG_7207.HEIC",
    "/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone/IMG_1323.JPG"
  ])
  ```
  Erwartet: 6 Stills importiert.

  > **Hinweis:** Resolve kann HEIC-Dateien möglicherweise nicht direkt importieren. Falls Import fehlschlägt:
  > ```bash
  > cd '/tmp'
  > for f in IMG_7159 IMG_7177 IMG_7187 IMG_7207; do
  >   sips -s format jpeg "/Users/Alex/Projects/Video Projekt ätna sizilen /I Phone/${f}.heic" --out "/tmp/${f}.jpg"
  > done
  > ```
  > Dann JPEGs importieren statt HEIC.

---

## Task 4: Intro auf Timeline legen

- [ ] **Schritt 4.1: Intro-Schwarzbild (Color Generator) einfügen**

  ```
  resolve_control(action="set_page", page="edit")
  timeline(action="set_current", index=<Sizilien_Erinnerung Index>)
  timeline(action="insert_generator", name="Solid Color")
  ```
  Erwartet: Generator auf Timeline platziert. Dauer manuell auf 2s (50 Frames @ 25fps) trimmen in Resolve.

- [ ] **Schritt 4.2: Intro-Titel einfügen**

  Playhead ans Ende des Schwarzbilds setzen:
  ```
  timeline(action="set_timecode", index=51)
  timeline(action="insert_title", name="Text+")
  ```
  Titel in Resolve öffnen (Doppelklick) und Text "Sizilien 2025" eintragen. Dauer: 3s (75 Frames). Fade-in/out je 0.5s (13 Frames) manuell in Resolve setzen.

---

## Task 5: Act 1 — Ätna DJI-Clips auf Timeline

DJI-Ordner aktivieren:
```
media_pool(action="set_current_folder", folder_name="Sizilien_DJI")
```

Für jeden Clip: `append_to_timeline` mit Clip-Namen-Filter, dann sofort auf Timeline prüfen.

- [ ] **Schritt 5.1: DJI_0934 (20s normal, Frames 0–499)**

  ```
  media_pool(action="append_to_timeline", file_paths=["DJI_0934_joined_stabilized.mp4"])
  ```
  *(AppendToTimeline platziert den ganzen Clip — in Resolve danach auf 20s = 500 Frames @ 25fps trimmen, oder startFrame/endFrame via Medienseite setzen)*

  > **Hinweis:** `append_to_timeline` unterstützt noch kein `startFrame`/`endFrame` direkt. Clips werden vollständig eingefügt und müssen in Resolve getrimmt werden — **oder** Task 5 verwendet `media_pool(action="create_timeline_from_clips")` mit In/Out-Points die vorher per `timeline_item` gesetzt wurden. Einfachster Weg: nach `append_to_timeline` die Clip-Enden in Resolve manuell trimmen während du die Timeline visuell kontrollierst.

- [ ] **Schritt 5.2: iPhone-Still IMG_7159 (3s)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_iPhone")
  media_pool(action="append_to_timeline", file_paths=["IMG_7159.heic"])
  ```
  *(oder `IMG_7159.jpg` falls HEIC konvertiert wurde)*
  Still auf 3s (75 Frames) trimmen.

- [ ] **Schritt 5.3: DJI_0936 (20s normal)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_DJI")
  media_pool(action="append_to_timeline", file_paths=["DJI_0936_stabilized_1.mp4"])
  ```

- [ ] **Schritt 5.4: iPhone-Still IMG_1302 (3s)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_iPhone")
  media_pool(action="append_to_timeline", file_paths=["IMG_1302.JPG"])
  ```

- [ ] **Schritt 5.5: DJI_0937 (15s normal)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_DJI")
  media_pool(action="append_to_timeline", file_paths=["DJI_0937_stabilized_1.mp4"])
  ```

- [ ] **Schritt 5.6: iPhone-Still IMG_7177 (3s)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_iPhone")
  media_pool(action="append_to_timeline", file_paths=["IMG_7177.heic"])
  ```

- [ ] **Schritt 5.7: DJI_0938 (15s normal + 5s SlowMo)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_DJI")
  media_pool(action="append_to_timeline", file_paths=["DJI_0938_stabilized_1.mp4"])
  ```
  Clip in Resolve auf 20s gesamt trimmen. Den letzten Teil (~5s = 125 Frames) via **Retime Controls** in Resolve auf 25% Speed setzen:
  - Rechtsklick auf Clip → Retime Controls
  - Letzten Abschnitt auf 25% setzen

  *(Alternativ: Clip in Resolve mit Blade teilen und letzten Teil via `timeline_item(action="set_property", property_name="Speed", property_value="25", item_index=<n>)` verlangsamen — falls SetProperty Speed unterstützt)*

- [ ] **Schritt 5.8: iPhone-Stills IMG_7187, IMG_7207, IMG_1323 (je 3s)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_iPhone")
  media_pool(action="append_to_timeline", file_paths=["IMG_7187.HEIC"])
  media_pool(action="append_to_timeline", file_paths=["IMG_7207.HEIC"])
  media_pool(action="append_to_timeline", file_paths=["IMG_1323.JPG"])
  ```
  Jedes Still auf 3s (75 Frames) trimmen.

- [ ] **Schritt 5.9: Act-1-Titel "Ätna — 3.357 m" einfügen**

  ```
  timeline(action="insert_title", name="Text+")
  ```
  Text in Resolve auf "Ätna — 3.357 m" setzen, Dauer 3s, Fade-in/out 0.5s.

---

## Task 6: Übergang Act 1 → Act 2 (Fade-to-Black)

- [ ] **Schritt 6.1: Fade-to-Black als Schwarzbild-Generator**

  ```
  timeline(action="insert_generator", name="Solid Color")
  ```
  Dauer 1s (25 Frames). In Resolve auf schwarz setzen.

  *(Oder: In Resolve am Ende des letzten Act-1-Clips einen Video-Fade-Out hinzufügen und am Anfang des ersten Act-2-Clips einen Fade-In)*

---

## Task 7: Act 2 — Pachino

- [ ] **Schritt 7.1: DJI_0940 mit Hero-Shot Balkon-Landung**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_DJI")
  media_pool(action="append_to_timeline", file_paths=["DJI_0940_stabilized.mp4"])
  ```
  Clip auf ~25s gesamt trimmen. Letzten ~5s (Balkon-Landung) in Resolve via Retime Controls auf 25% Speed setzen → ergibt ~20s SlowMo am Ende des Clips für den Hero-Shot.

- [ ] **Schritt 7.2: Act-2-Titel "Pachino — Casa Tino"**

  ```
  timeline(action="insert_title", name="Text+")
  ```
  Text setzen, Dauer 3s, Fade 0.5s.

---

## Task 8: Übergang Act 2 → Act 3

- [ ] **Schritt 8.1: Fade-to-Black (1s)**

  ```
  timeline(action="insert_generator", name="Solid Color")
  ```
  Dauer 25 Frames, schwarz.

---

## Task 9: Act 3 — Küste

- [ ] **Schritt 9.1: DJI_0942 (20s)**

  ```
  media_pool(action="set_current_folder", folder_name="Sizilien_DJI")
  media_pool(action="append_to_timeline", file_paths=["DJI_0942_stabilized.mp4"])
  ```

- [ ] **Schritt 9.2: DJI_0943 (20s)**

  ```
  media_pool(action="append_to_timeline", file_paths=["DJI_0943_stabilized.mp4"])
  ```

- [ ] **Schritt 9.3: DJI_0947 (20s)**

  ```
  media_pool(action="append_to_timeline", file_paths=["DJI_0947_stabilized.mp4"])
  ```

- [ ] **Schritt 9.4: Act-3-Titel "Sizilianische Küste"**

  ```
  timeline(action="insert_title", name="Text+")
  ```

---

## Task 10: Outro

- [ ] **Schritt 10.1: Fade-to-Black (2s)**

  ```
  timeline(action="insert_generator", name="Solid Color")
  ```
  Dauer 50 Frames, schwarz.

- [ ] **Schritt 10.2: Outro-Titel "Alex & Tino — Sizilien 2025"**

  ```
  timeline(action="insert_title", name="Text+")
  ```
  Dauer 4s (100 Frames), Fade-in/out 0.5s.

- [ ] **Schritt 10.3: Abschließendes Fade-to-Black (2s)**

  ```
  timeline(action="insert_generator", name="Solid Color")
  ```
  Dauer 50 Frames, schwarz.

---

## Task 11: Color Grading — LUT auf alle DJI-Clips

- [ ] **Schritt 11.1: Auf Color-Seite wechseln**

  ```
  resolve_control(action="set_page", page="color")
  ```

- [ ] **Schritt 11.2: LUT-Pfad ermitteln**

  Indexierter LUT-Name (aus letztem Projekt bekannt):
  ```
  color(action="get_lut", node_index=1)
  ```
  Erwartet: Rückgabe des bekannten `DJI_X7_DLOG2Rec709.cube` Pfads.

- [ ] **Schritt 11.3: LUT auf jeden DJI-Clip setzen**

  Für jeden DJI-Clip (item_index 0–7 auf Video Track 1, je nach finaler Position — vorher `timeline(action="get_items", track_type="video", track_index=1)` aufrufen um Indizes zu bestätigen):

  ```
  timeline(action="set_timecode", index=<frame_mitten_im_clip>)
  color(action="set_lut", node_index=1, lut_path="DJI/DJI_X7_DLOG2Rec709.cube")
  ```
  *(Playhead-Workaround: vor `set_lut` immer `set_timecode` auf einen Frame innerhalb des Ziel-Clips aufrufen)*

  Alle 8 DJI-Clips durchgehen. iPhone-Stills und Titel überspringen.

- [ ] **Schritt 11.4: Auto-Grade auf alle Clips**

  ```
  color(action="auto_grade", node_index=0.42)
  ```
  Erwartet: Alle Timeline-Clips werden auf Ziel-Luma 0.42 angepasst.

---

## Task 12: Speichern und visuell kontrollieren

- [ ] **Schritt 12.1: Projekt speichern**

  ```
  project(action="save")
  ```

- [ ] **Schritt 12.2: Auf Edit-Seite zurück und Timeline durchschauen**

  ```
  resolve_control(action="set_page", page="edit")
  ```
  In Resolve: Timeline von Anfang bis Ende abspielen, Trimming der Clips visuell prüfen, Titel-Texte kontrollieren, SlowMo-Momente prüfen.

- [ ] **Schritt 12.3: Finales Speichern**

  ```
  project(action="save")
  ```

---

## Bekannte Workarounds (Referenz)

| Problem | Lösung |
|---|---|
| Stale MCP-Prozess | `kill $(pgrep -f "davinci-resolve-mcp/src/server.py")` |
| `set_lut` schlägt fehl | Playhead per `set_timecode` navigieren, dann LUT setzen |
| HEIC-Import schlägt fehl | Vorher per `sips` zu JPEG konvertieren |
| Clip wird vollständig eingefügt | In Resolve manuell trimmen (SplitClip nicht verfügbar via API) |
| Titel-Text bleibt leer | In Resolve manuell per Doppelklick auf Titel editieren |
| SlowMo per API nicht setzbar | In Resolve: Rechtsklick → Retime Controls |
