# DaVinci Resolve Scripting API Reference

> Wird in Phase 0 mit Daten aus der offiziellen Doku und Referenz-Repos befüllt.

## API-Objekthierarchie

```
Resolve
├── ProjectManager
│   └── Project
│       ├── MediaPool
│       │   ├── Folder
│       │   └── MediaPoolItem
│       ├── Timeline
│       │   ├── TimelineItem
│       │   └── Track
│       ├── Gallery
│       │   └── GalleryStillAlbum
│       └── RenderJob
├── MediaStorage
└── Fusion
    └── FusionComp
```

## Einstiegspunkt

```python
import DaVinciResolveScript as dvr
resolve = dvr.scriptapp("Resolve")
```

## Wichtige Methoden

_Wird nach Analyse der Referenz-Repos und offiziellen Doku ergänzt._
