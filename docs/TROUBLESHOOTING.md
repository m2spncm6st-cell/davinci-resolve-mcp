# Troubleshooting

## Bekannte Probleme & Lösungen

### Python 3.13+ ABI-Inkompatibilität

**Problem**: `fusionscript.so` ist nicht mit Python 3.13+ kompatibel.
**Lösung**: Python 3.10–3.12 verwenden (pyenv empfohlen).

### "Could not connect to DaVinci Resolve"

**Checkliste**:
1. Ist DaVinci Resolve gestartet?
2. Preferences > General > External scripting using → "Local"?
3. Sind die Umgebungsvariablen korrekt gesetzt?
4. Resolve nach Änderung der Einstellung neu gestartet?

### MCP Timeout

**Problem**: Claude Code meldet Timeout beim Verbinden.
**Lösung**: `MCP_TIMEOUT=10000 claude` verwenden.

### fusionscript.so nicht gefunden

**Erwarteter Pfad**: `/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so`
**Lösung**: Pfad in `.mcp.json` bzw. Umgebungsvariablen anpassen.
