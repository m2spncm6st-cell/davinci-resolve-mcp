# Design: Sizilien Erinnerungsvideo

**Datum:** 2026-03-29
**Projekt:** Alex & Tino — Sizilien 2025
**Ziel:** Cinematisches Erinnerungsvideo, 3–5 Minuten, für Alex und Tino

---

## Quellmaterial

**Projektordner:** `/Users/Alex/Projects/Video Projekt ätna sizilen ` *(trailing space im Ordnernamen)*

### DJI-Clips (alle 4K HEVC, 100fps, D-Log M)

| Clip | Dauer | Akt |
|---|---|---|
| DJI_0934_joined_stabilized.mp4 | 271s | Ätna |
| DJI_0936_stabilized_1.mp4 | 192s | Ätna |
| DJI_0937_stabilized_1.mp4 | 153s | Ätna |
| DJI_0938_stabilized_1.mp4 | 169s | Ätna |
| DJI_0940_stabilized.mp4 | 91s | Pachino / Balkon-Landung |
| DJI_0942_stabilized.mp4 | 193s | Küste |
| DJI_0943_stabilized.mp4 | 164s | Küste |
| DJI_0947_stabilized.mp4 | 44s | Küste |

### iPhone-Stills (alle aus Etna-Tag, Jun 7–8 2025)

Alle 92 iPhone-Dateien stammen ausschließlich vom Ätna-Tag. Kein iPhone-Material für Pachino oder Küste vorhanden.

**Ausgewählte Fotos für Act 1:**

| Datei | Inhalt |
|---|---|
| IMG_7159.heic | Sonnenaufgang über der Etna-Villa mit Pool — Stimmungsshot |
| IMG_1302.JPG | Ätna von unten mit Lavafeld und Kiefern — Establishing Shot |
| IMG_7177.heic | Offizielles ETNA-Schild mit rauchendem Krater — ikonisch |
| IMG_7187.HEIC | Tino am Gipfel lächelnd, Krater hinter ihm — Charakter-Moment |
| IMG_7207.HEIC | Tino posiert mit Gipfelkegel — lustige Serie |
| IMG_1323.JPG | Blick hinunter in den Krater — dramatisch |

---

## Timeline

**Name:** `Sizilien_Erinnerung`
**Format:** 4K (3840×2160), 25fps, Rec.709
**Verhalten 100fps-Clips auf 25fps-Timeline:** Clip-Speed explizit auf 25% setzen → ×4 Zeitlupe (Resolve macht das NICHT automatisch)

### Schnittfolge

```
[INTRO]
  Schwarzbild 2s
  Fade-in → Titel "Sizilien 2025" (3s) → Fade-out

[ACT 1 — ÄTNA]  ca. 100s
  DJI_0934  25s  (startFrame 0)
  STILL: IMG_7159   3s
  DJI_0936  20s  (startFrame 0)
  STILL: IMG_1302   3s
  DJI_0937  20s  (startFrame 0)
  STILL: IMG_7177   3s
  DJI_0938  20s  (startFrame 0)
  STILL: IMG_7187   3s
  STILL: IMG_7207   3s
  STILL: IMG_1323   3s
  Titel: "Ätna — 3.357 m"

[ÜBERGANG]  Fade-to-black 1s

[ACT 2 — PACHINO]  ca. 30s
  DJI_0940  Clip-Speed 25% → ganzer Clip wird zu ~366s, davon 30s verwenden
  Hero-Shot: letzten ~10s Echtzeit (Balkon-Landung) = ~40s SlowMo auf Timeline
  Titel: "Pachino — Casa Tino"

[ÜBERGANG]  Fade-to-black 1s

[ACT 3 — KÜSTE]  ca. 60s
  DJI_0942  20s  (startFrame 0)
  DJI_0943  20s  (startFrame 0)
  DJI_0947  20s  (startFrame 0)
  Titel: "Sizilianische Küste"

[OUTRO]
  Fade-to-black 2s
  Titel: "Alex & Tino — Sizilien 2025" (4s)
  Fade-to-black 2s
```

---

## Color Grading

- **LUT:** Bestehend indexierte `DJI_X7_DLOG2Rec709.cube` (enthält Zeb-Gardner-angepasste D-Log M → Rec.709 LUT aus vorherigem Projekt)
  - Pfad: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/`
  - Workaround: `set_lut` benötigt bereits indexierten Pfad → bestehende .cube wird verwendet
- **Auto-Grade:** Ziel-Luma 0.42 (heller, warm, Urlaubsgefühl)
- **iPhone-Stills:** Kein Grading (bereits Rec.709)

---

## Texttitel

Alle Titel: Resolve Fusion Text, weiß, zentriert, Fade-in/out je 0.5s

| Titel | Position |
|---|---|
| "Sizilien 2025" | Intro |
| "Ätna — 3.357 m" | Ende Act 1 |
| "Pachino — Casa Tino" | Ende Act 2 |
| "Sizilianische Küste" | Ende Act 3 |
| "Alex & Tino — Sizilien 2025" | Outro |

---

## Audio

- Track 1: leer — Musik wird später manuell in Resolve eingefügt
- Stil-Referenz: warmer Soul/Hip-Hop, Urlaubsfeeling (Referenz: "Let the Sun Shine" — Nas)

---

## Technische Rahmenbedingungen

- **MCP-Server:** `~/Projects/davinci-resolve-mcp` — DaVinci Resolve MCP v1.7.0
- **Resolve:** DaVinci Resolve Studio 20.3.1, macOS Apple Silicon
- **Python:** 3.12.11 via pyenv (System-Python 3.14 inkompatibel)
- **ffprobe:** `/Users/Alex/.local/bin/ffprobe`

### Bekannte Workarounds
- Stale MCP-Prozess: `kill $(pgrep -f "davinci-resolve-mcp/src/server.py")`
- `set_lut`: Playhead per `set_timecode` vor Zuweisung navigieren
- `SplitClip` nicht verfügbar → `append_to_timeline` mit `startFrame`/`endFrame`
- `AddMarker` schlägt fehl bei leerem `name=""` → immer non-empty name übergeben
- Neue .cube LUT-Dateien erst nach Resolve-Neustart sichtbar

---

## Vorgehen (Ansatz A — Vollautomatisch)

Ein einziger Durchlauf per MCP:
1. `resolve_status()` — Verbindung prüfen
2. Timeline `Sizilien_Erinnerung` anlegen (4K, 25fps)
3. Alle Clips + Stills in Schnittfolge auf Timeline legen
4. LUT + Auto-Grade auf alle DJI-Clips anwenden
5. Texttitel setzen
6. Audio Track 1 leer lassen
7. Visuell in Resolve kontrollieren
