# DaVinci Resolve Scripting API Reference

> Quelle: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/README.txt`
> Stand: 7. Oktober 2025 (Resolve 20.x)

## Einstiegspunkt

```python
import DaVinciResolveScript as dvr
resolve = dvr.scriptapp("Resolve")
```

## API-Objekthierarchie

```
Resolve
├── Fusion
├── MediaStorage
├── ProjectManager
│   └── Project
│       ├── MediaPool
│       │   ├── Folder
│       │   │   └── MediaPoolItem
│       │   └── MediaPoolItem
│       ├── Timeline
│       │   └── TimelineItem
│       │       ├── Graph (Node-Graph pro Clip/Layer)
│       │       └── fusionComp
│       ├── Gallery
│       │   └── GalleryStillAlbum
│       │       └── GalleryStill
│       ├── ColorGroup
│       └── Graph (Timeline-Level Node-Graph)
```

## Pages / Workspaces

`resolve.OpenPage(pageName)` / `resolve.GetCurrentPage()`:

| Wert | Beschreibung |
|---|---|
| `"media"` | Media Page |
| `"cut"` | Cut Page |
| `"edit"` | Edit Page |
| `"fusion"` | Fusion Page |
| `"color"` | Color Page |
| `"fairlight"` | Fairlight Page |
| `"deliver"` | Deliver Page |

---

## Resolve

| Methode | Rückgabe |
|---|---|
| `GetProjectManager()` | ProjectManager |
| `GetMediaStorage()` | MediaStorage |
| `Fusion()` | Fusion |
| `OpenPage(pageName)` | Bool |
| `GetCurrentPage()` | string |
| `GetProductName()` | string |
| `GetVersion()` | [major, minor, patch, build, suffix] |
| `GetVersionString()` | string |
| `Quit()` | None |
| `LoadLayoutPreset(name)` | Bool |
| `SaveLayoutPreset(name)` | Bool |
| `ImportRenderPreset(path)` | Bool |
| `ExportRenderPreset(name, path)` | Bool |
| `GetKeyframeMode()` | int |
| `SetKeyframeMode(mode)` | Bool |

---

## ProjectManager

| Methode | Rückgabe |
|---|---|
| `GetCurrentProject()` | Project |
| `LoadProject(name)` | Project |
| `CreateProject(name, mediaPath?)` | Project |
| `DeleteProject(name)` | Bool |
| `SaveProject()` | Bool |
| `CloseProject(project)` | Bool |
| `GetProjectListInCurrentFolder()` | [names] |
| `GetFolderListInCurrentFolder()` | [names] |
| `CreateFolder(name)` | Bool |
| `DeleteFolder(name)` | Bool |
| `OpenFolder(name)` | Bool |
| `GotoRootFolder()` | Bool |
| `GotoParentFolder()` | Bool |
| `ImportProject(path, name?)` | Bool |
| `ExportProject(name, path, withStills?)` | Bool |
| `GetCurrentDatabase()` | {DbType, DbName, IpAddress} |
| `GetDatabaseList()` | [{dbInfo}] |
| `SetCurrentDatabase({dbInfo})` | Bool |

---

## Project

| Methode | Rückgabe |
|---|---|
| `GetMediaPool()` | MediaPool |
| `GetTimelineCount()` | int |
| `GetTimelineByIndex(idx)` | Timeline (1-basiert!) |
| `GetCurrentTimeline()` | Timeline |
| `SetCurrentTimeline(timeline)` | Bool |
| `GetGallery()` | Gallery |
| `GetName()` / `SetName(name)` | string / Bool |
| `GetSetting(key)` / `SetSetting(key, val)` | string / Bool |
| `AddRenderJob()` | string (job ID) |
| `DeleteRenderJob(jobId)` | Bool |
| `DeleteAllRenderJobs()` | Bool |
| `GetRenderJobList()` | [jobs] |
| `StartRendering(...)` | Bool |
| `StopRendering()` | None |
| `IsRenderingInProgress()` | Bool |
| `SetRenderSettings({settings})` | Bool |
| `GetRenderJobStatus(jobId)` | {status} |
| `GetRenderFormats()` | {format: ext} |
| `GetRenderCodecs(format)` | {desc: name} |
| `GetCurrentRenderFormatAndCodec()` | {format, codec} |
| `SetCurrentRenderFormatAndCodec(fmt, codec)` | Bool |
| `GetPresetList()` | [presets] |
| `LoadRenderPreset(name)` | Bool |
| `RefreshLUTList()` | Bool |
| `GetUniqueId()` | string |
| `GetColorGroupsList()` | [ColorGroups] |
| `AddColorGroup(name)` | ColorGroup |
| `DeleteColorGroup(group)` | Bool |
| `ExportCurrentFrameAsStill(path)` | Bool |

---

## MediaStorage

| Methode | Rückgabe |
|---|---|
| `GetMountedVolumeList()` | [paths] |
| `GetSubFolderList(path)` | [paths] |
| `GetFileList(path)` | [paths] |
| `RevealInStorage(path)` | Bool |
| `AddItemListToMediaPool(...)` | [clips] |
| `AddClipMattesToMediaPool(item, [paths])` | Bool |

---

## MediaPool

| Methode | Rückgabe |
|---|---|
| `GetRootFolder()` | Folder |
| `GetCurrentFolder()` | Folder |
| `SetCurrentFolder(folder)` | Bool |
| `AddSubFolder(folder, name)` | Folder |
| `RefreshFolders()` | Bool |
| `CreateEmptyTimeline(name)` | Timeline |
| `AppendToTimeline(...)` | [TimelineItem] |
| `CreateTimelineFromClips(name, ...)` | Timeline |
| `ImportTimelineFromFile(path, options?)` | Timeline |
| `DeleteTimelines([timelines])` | Bool |
| `DeleteClips([clips])` | Bool |
| `MoveClips([clips], target)` | Bool |
| `ImportMedia([items])` | [MediaPoolItems] |
| `ExportMetadata(fileName, [clips]?)` | Bool |
| `RelinkClips([items], path)` | Bool |
| `UnlinkClips([items])` | Bool |
| `GetUniqueId()` | string |
| `GetSelectedClips()` | [MediaPoolItems] |
| `SetSelectedClip(item)` | Bool |

---

## Folder

| Methode | Rückgabe |
|---|---|
| `GetName()` | string |
| `GetClipList()` | [clips] |
| `GetSubFolderList()` | [folders] |
| `GetUniqueId()` | string |
| `Export(path)` | bool |
| `TranscribeAudio()` | Bool |

---

## MediaPoolItem

| Methode | Rückgabe |
|---|---|
| `GetName()` / `SetName(name)` | string / bool |
| `GetMetadata(type?)` | string/dict |
| `SetMetadata(type, val)` / `SetMetadata({meta})` | Bool |
| `GetMediaId()` | string |
| `GetClipProperty(key?)` | string/dict |
| `SetClipProperty(key, val)` | Bool |
| `AddMarker(frame, color, name, note, dur, data?)` | Bool |
| `GetMarkers()` | {frameId: {info}} |
| `DeleteMarkersByColor(color)` | Bool |
| `DeleteMarkerAtFrame(frame)` | Bool |
| `AddFlag(color)` / `GetFlagList()` / `ClearFlags(color)` | Bool / [colors] / Bool |
| `GetClipColor()` / `SetClipColor(name)` / `ClearClipColor()` | string / Bool / Bool |
| `LinkProxyMedia(path)` / `UnlinkProxyMedia()` | Bool |
| `ReplaceClip(path)` | Bool |
| `GetUniqueId()` | string |
| `TranscribeAudio()` / `ClearTranscription()` | Bool |
| `GetAudioMapping()` | JSON string |

---

## Timeline

| Methode | Rückgabe |
|---|---|
| `GetName()` / `SetName(name)` | string / Bool |
| `GetStartFrame()` / `GetEndFrame()` | int |
| `GetStartTimecode()` / `SetStartTimecode(tc)` | string / Bool |
| `GetCurrentTimecode()` / `SetCurrentTimecode(tc)` | string / Bool |
| `GetTrackCount(trackType)` | int |
| `AddTrack(type, subType?)` | Bool |
| `DeleteTrack(type, idx)` | Bool |
| `GetTrackName(type, idx)` / `SetTrackName(type, idx, name)` | string / Bool |
| `SetTrackEnable(type, idx, bool)` / `GetIsTrackEnabled(type, idx)` | Bool |
| `SetTrackLock(type, idx, bool)` / `GetIsTrackLocked(type, idx)` | Bool |
| `GetItemListInTrack(type, idx)` | [items] |
| `DeleteClips([items], bool?)` | Bool |
| `GetCurrentVideoItem()` | item |
| `AddMarker(...)` / `GetMarkers()` | Bool / {markers} |
| `GetSetting(key)` / `SetSetting(key, val)` | string / Bool |
| `DuplicateTimeline(name?)` | timeline |
| `CreateCompoundClip([items], {info}?)` | timelineItem |
| `CreateFusionClip([items])` | timelineItem |
| `InsertGeneratorIntoTimeline(name)` | TimelineItem |
| `InsertTitleIntoTimeline(name)` | TimelineItem |
| `InsertFusionTitleIntoTimeline(name)` | TimelineItem |
| `Export(fileName, type, subtype)` | Bool |
| `GrabStill()` | galleryStill |
| `GetUniqueId()` | string |
| `GetNodeGraph()` | Graph |
| `DetectSceneCuts()` | Bool |
| `GetMediaPoolItem()` | MediaPoolItem |

**Track-Typen:** `"video"`, `"audio"`, `"subtitle"`

---

## TimelineItem

| Methode | Rückgabe |
|---|---|
| `GetName()` / `SetName(name)` | string / bool |
| `GetDuration()` / `GetStart()` / `GetEnd()` | int |
| `GetLeftOffset()` / `GetRightOffset()` | int |
| `GetProperty(key?)` / `SetProperty(key, val)` | int/dict / Bool |
| `GetFusionCompCount()` | int |
| `GetFusionCompByIndex(idx)` / `GetFusionCompByName(name)` | fusionComp |
| `GetFusionCompNameList()` | [names] |
| `AddFusionComp()` | fusionComp |
| `ImportFusionComp(path)` | fusionComp |
| `ExportFusionComp(path, idx)` | Bool |
| `AddVersion(name, type)` | Bool |
| `GetCurrentVersion()` | {name, type} |
| `GetMediaPoolItem()` | MediaPoolItem |
| `AddMarker(...)` / `GetMarkers()` | Bool / {markers} |
| `SetCDL([CDL])` | Bool |
| `CopyGrades([targets])` | Bool |
| `SetClipEnabled(bool)` / `GetClipEnabled()` | Bool |
| `GetNodeGraph(layerIdx?)` | Graph |
| `GetColorGroup()` | ColorGroup |
| `AssignToColorGroup(group)` | Bool |
| `Stabilize()` / `SmartReframe()` | Bool |
| `GetLinkedItems()` | [TimelineItems] |

---

## Graph (Node-Graph)

| Methode | Rückgabe |
|---|---|
| `GetNumNodes()` | int |
| `SetLUT(nodeIdx, path)` / `GetLUT(nodeIdx)` | Bool / string |
| `GetNodeLabel(nodeIdx)` | string |
| `GetToolsInNode(nodeIdx)` | [tools] |
| `SetNodeEnabled(nodeIdx, bool)` | Bool |
| `ApplyGradeFromDRX(path, mode)` | Bool |
| `ResetAllGrades()` | Bool |

Node-Indices sind **1-basiert**.

---

## Gallery / GalleryStillAlbum

| Methode | Rückgabe |
|---|---|
| `Gallery.GetCurrentStillAlbum()` | album |
| `Gallery.SetCurrentStillAlbum(album)` | Bool |
| `Gallery.GetGalleryStillAlbums()` | [albums] |
| `Album.GetStills()` | [stills] |
| `Album.GetLabel(still)` / `SetLabel(still, label)` | string / Bool |
| `Album.ImportStills([paths])` | Bool |
| `Album.ExportStills([stills], folder, prefix, format)` | Bool |

---

## ColorGroup

| Methode | Rückgabe |
|---|---|
| `GetName()` / `SetName(name)` | string / Bool |
| `GetClipsInTimeline(timeline?)` | [TimelineItem] |
| `GetPreClipNodeGraph()` | Graph |
| `GetPostClipNodeGraph()` | Graph |

---

## macOS-Umgebungsvariablen

```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"
```

## Render Settings Keys

SelectAllFrames, MarkIn, MarkOut, TargetDir, CustomName, UniqueFilenameStyle,
ExportVideo, ExportAudio, FormatWidth, FormatHeight, FrameRate,
PixelAspectRatio, VideoQuality, AudioCodec, AudioBitDepth, AudioSampleRate,
ColorSpaceTag, GammaTag, ExportAlpha, EncodingProfile, MultiPassEncode,
AlphaMode, NetworkOptimization

## Timeline Export Formate

AAF, DRT, EDL, FCP_7_XML, FCPXML_1_8, FCPXML_1_9, FCPXML_1_10,
HDR_10_PROFILE_A/B, TEXT_CSV, TEXT_TAB, DOLBY_VISION_VER_2_9/4_0/5_1,
OTIO, ALE, ALE_CDL
