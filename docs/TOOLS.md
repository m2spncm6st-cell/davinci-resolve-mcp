# Tool-Referenz

Vollständige Übersicht aller MCP-Tools und Actions. Stand: v1.4.0

---

## resolve_status()

Verbindungsstatus prüfen. Immer als erstes aufrufen.

```
resolve_status()
→ connected, version, project, page
```

---

## resolve_control(action, page)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `status` | — | Wie resolve_status() |
| `get_page` | — | Aktuelle Seite |
| `set_page` | page | Seite wechseln (media\|cut\|edit\|fusion\|color\|fairlight\|deliver) |
| `get_version` | — | Resolve-Version |

---

## project(action, name)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `list` | — | Alle Projekte |
| `get_current` | — | Aktuelles Projekt |
| `open` | name | Projekt öffnen |
| `save` | — | Speichern |
| `create` | name | Neues Projekt |
| `close` | — | Schließen |

---

## timeline(action, name, index, track_type, track_index, export_format, file_path)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `list` | — | Alle Timelines |
| `get_current` | — | Aktuelle Timeline |
| `set_current` | name | Timeline aktivieren |
| `create` | name | Neue Timeline |
| `get_tracks` | track_type | Tracks auflisten |
| `get_items` | track_type, track_index | Clips in einem Track |
| `get_markers` | — | Alle Marker |
| `add_marker` | track_index (frame), name (color) | Marker setzen |
| `delete_markers` | name (color) | Marker löschen |
| `get_settings` | — | Timeline-Einstellungen |
| `duplicate` | name | Timeline duplizieren |
| `add_track` | track_type | Track hinzufügen |
| `delete_track` | track_type, track_index | Track löschen |
| `export` | file_path, export_format | Exportieren (FCPXML, EDL, …) |
| `insert_title` | name | Titel einfügen |
| `insert_generator` | name | Generator einfügen |
| `delete_clips` | track_type, track_index | Alle Clips in Track löschen |
| `get_marker_clips` | name (color, optional) | Clips die mit Markern überlappen |
| `split_at_markers` | name (color, optional) | Clips an Markern aufsplitten |
| `delete_between_markers` | track_index (marker_a_frame), index (marker_b_frame) | Clips zwischen zwei Frames löschen |
| `rename_clips_from_markers` | name (color, optional) | Clips nach nächstem Marker benennen |

---

## timeline_item(action, track_type, track_index, item_index, property_name, property_value, clip_color)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `get_current` | — | Aktueller Clip |
| `get_properties` | track_type, track_index, item_index | Alle Eigenschaften |
| `set_property` | track_type, track_index, item_index, property_name, property_value | Eigenschaft setzen |
| `get_info` | track_type, track_index, item_index | Clip-Infos |
| `set_clip_color` | track_type, track_index, item_index, clip_color | Farbe setzen |
| `clear_clip_color` | track_type, track_index, item_index | Farbe entfernen |
| `set_enabled` | track_type, track_index, item_index, property_value | Aktivieren/deaktivieren |
| `get_source_info` | track_type, track_index, item_index | Quelldatei-Infos |

---

## media_pool(action, folder_name, file_paths, timeline_name)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `list_folders` | — | Alle Ordner |
| `get_current_folder` | — | Aktueller Ordner |
| `set_current_folder` | folder_name | Ordner wechseln |
| `create_folder` | folder_name | Ordner erstellen |
| `delete_folder` | folder_name | Ordner löschen |
| `list_clips` | — | Clips im aktuellen Ordner |
| `get_clip_info` | — | Clip-Infos |
| `import_media` | file_paths | Medien importieren |
| `create_timeline_from_clips` | timeline_name | Timeline aus Clips |
| `get_root_folder` | — | Root-Ordner |
| `selected_clips` | — | Ausgewählte Clips |
| `append_to_timeline` | — | Zu Timeline hinzufügen |

---

## color(action, node_index, lut_path, item_index)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `get_current_item` | — | Aktueller Clip auf Color-Page |
| `get_node_graph` | — | Node-Graph |
| `get_nodes` | — | Alle Nodes |
| `get_lut` | node_index | LUT eines Nodes |
| `set_lut` | node_index, lut_path | LUT setzen |
| `set_node_enabled` | node_index | Node aktivieren/deaktivieren |
| `reset_grades` | — | Grading zurücksetzen |
| `get_color_groups` | — | Color-Gruppen |
| `get_timeline_nodes` | — | Timeline-Nodes |

---

## deliver(action, preset_name, target_dir, file_name, render_format, render_codec, job_id)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `get_formats` | — | Verfügbare Formate |
| `get_codecs` | render_format | Codecs für Format |
| `get_presets` | — | Render-Presets |
| `load_preset` | preset_name | Preset laden |
| `get_current_format` | — | Aktuelles Format/Codec |
| `set_format` | render_format, render_codec | Format setzen |
| `set_render_settings` | target_dir, file_name | Output-Einstellungen |
| `add_job` | — | Job zur Queue hinzufügen |
| `list_jobs` | — | Alle Jobs |
| `get_job_status` | job_id | Job-Status |
| `start_render` | job_id (optional) | Rendern starten |
| `stop_render` | — | Rendern stoppen |
| `is_rendering` | — | Render-Status |
| `delete_all_jobs` | — | Queue leeren |

**Typischer Workflow:**
```
deliver(action="load_preset", preset_name="H.264 Master")
deliver(action="set_render_settings", target_dir="~/Desktop", file_name="output")
deliver(action="add_job")
deliver(action="start_render")
deliver(action="is_rendering")  # wiederholen bis False
```

---

## fusion(action, comp_name, comp_index, file_path, new_name)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `list_comps` | — | Alle Fusion Comps |
| `get_comp` | comp_index | Comp abrufen |
| `add_comp` | — | Neue Comp |
| `import_comp` | file_path | Comp importieren |
| `export_comp` | comp_index, file_path | Comp exportieren |
| `delete_comp` | comp_index | Comp löschen |
| `rename_comp` | comp_index, new_name | Comp umbenennen |
| `insert_fusion_clip` | — | Fusion Clip einfügen |

---

## transition(action, track_type, track_index, item_index, transition_type, duration)

Neu in v1.3.0.

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `list_types` | — | Verfügbare Typen: Cut, Dissolve, DipToColor, Wipe |
| `get` | track_type, track_index, item_index | Transition an Clip lesen |
| `add` | track_type, track_index, item_index, transition_type, duration | Übergang einfügen |
| `remove` | track_type, track_index, item_index | Übergang entfernen |

**Beispiel:** Dissolve nach Clip 1, 24 Frames:
```
transition(action="add", track_type="video", track_index=1, item_index=1,
           transition_type="Dissolve", duration=24)
```

---

## fairlight(action, track_index, item_index, volume, muted, pan, duration)

| Action | Parameter | Beschreibung |
|--------|-----------|--------------|
| `get_audio_tracks` | — | Alle Audio-Tracks |
| `get_audio_items` | track_index | Clips in Audio-Track |
| `get_volume` | track_index, item_index | Lautstärke lesen |
| `set_volume` | track_index, item_index, volume | Lautstärke setzen (dB) |
| `set_mute` | track_index, muted | Track muten/unmuten |
| `set_pan` | track_index, item_index, pan | Pan setzen (-1.0 bis 1.0) |
| `fade_in` | track_index, item_index, duration | Fade-In setzen (Frames) |
| `fade_out` | track_index, item_index, duration | Fade-Out setzen (Frames) |

**Beispiel:** Lautstärke auf -6 dB, Fade-Out 48 Frames:
```
fairlight(action="set_volume", track_index=1, item_index=1, volume=-6.0)
fairlight(action="fade_out", track_index=1, item_index=1, duration=48)
```

---

## Hinweise

- Alle Indizes sind **1-basiert**
- `track_type`: `"video"` oder `"audio"`
- Resolve muss laufen, External Scripting auf **"Local"**
- Bei API-Einschränkungen gibt das Tool `success: false` mit Fehlermeldung zurück — kein Crash
