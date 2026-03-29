# Cinematic Drone Edit — Dramatic & Moody

## Ziel
Professioneller cinematic Edit eines 4K/100fps Drohnen-Clips (DJI_0992_joined_stabilized.mp4, ~3:37) ohne Sound. Dramatischer, moody Look mit starkem Kontrast und tiefen Schatten.

## Quell-Material
- **Clip:** DJI_0992_joined_stabilized.mp4
- **Auflösung:** 3840x2160 (4K)
- **Framerate:** 100fps Quelle, 29.97fps Timeline
- **Dauer:** ~3:37 (6521 Frames @ 29.97fps)
- **Status:** Bereits stabilisiert, 1 Node "Auto Color", alle Properties default

## Output
- 4K (3840x2160), 29.97fps
- Kein Audio

## Workflow

### 1. Vorbereitung
- Timeline "Test Timeline" duplizieren → "Cinematic Edit"
- Auf Kopie arbeiten, Original bleibt unberührt

### 2. Segmentierung (Marker-Based Editing)
- 5-6 Marker in ~30s Intervallen über den Clip verteilen
- An Markern splitten → 5-6 Segmente
- Alle Segmente behalten (User entscheidet nachher manuell)

### 3. Reframing
Abwechselnde Zoom/Pan-Varianten pro Segment:

| Segment | ZoomX | Pan | Tilt |
|---------|-------|-----|------|
| 1 | 1.0 (Wide) | 0 | 0 |
| 2 | 1.15 | 30 | 0 |
| 3 | 1.0 (Wide) | 0 | 0 |
| 4 | 1.2 | 0 | 20 |
| 5 | 1.0 (Wide) | 0 | 0 |
| 6 | 1.1 | -20 | 0 |

### 4. Transitions
- Cross Dissolve zwischen allen Schnitten
- Dauer: 24 Frames (~0.8s)

### 5. Color Grade — Multi-Node Dramatic Look

| Node | Funktion | Details |
|------|----------|---------|
| 1 | Contrast & Exposure | Lift runter (tiefe Schatten), Gain leicht runter |
| 2 | Color Shift | Schatten → Teal/Blau, Highlights leicht warm |
| 3 | Saturation | Gesamtsättigung reduzieren (~70-80%) |

### 6. Bekannte Limitationen (API)
- **Slow-Motion:** Retime nicht per Scripting API steuerbar → manuell nachziehen
- **Power Windows/Vignette:** Nicht per API erstellbar → manuell nachziehen
- **Keyframed Movements:** API setzt statische Werte, kein Keyframing

## Implementierungs-Status (2026-03-29)

### ✅ Abgeschlossen
- Timeline "Cinematic Final" erstellt (Duplikat von "Test Timeline")
- 6 Segmente á ~1086 Frames via AppendToTimeline (In/Out-Points Workaround)
- Reframing pro Segment (ZoomX/Pan/Tilt via SetProperty)
- Marker mit Non-Empty-Names (AddMarker-Fix)
- **Color Grade:** Zeb Gardner D-LOG-M → Rec.709 LUT (6.9MB, 65x65x65, reverse-engineered)
- **CDL per Segment:** Dramatisches Grading (warme Highlights, teal Schatten, moody Desaturation 0.72–0.78)
- Indexed-LUT-Workaround: Punchy_FPV_DJI_O3.cube temporär mit Zeb Gardner Inhalt überschrieben

### ⚠️ Manuell nachziehen
- Slow-Motion (Retime) für gewünschte Sequenzen
- Transitions (Cmd+T in Resolve — API in 20.3 nicht verfügbar)
- Power Window / Vignette für Finishing

### 🎬 Professioneller Workflow (Recherche-Ergebnis)
- **Quellen:** zebgardner.com, hueman.com, FPV-Community (Reddit/YouTube)
- **Empfehlung:** Zeb Gardner D-Log M LUT → ASC CDL → (optional) Noise Reduction
- **Wichtig für D-Log M:** Shadow Lift (+0.03), Saturation korrigieren (0.87), kein CST verwenden
