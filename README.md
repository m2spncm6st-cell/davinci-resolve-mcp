# DaVinci Resolve MCP Server

MCP-Server für die Steuerung von DaVinci Resolve via Claude Code.

## Voraussetzungen

- macOS (Apple Silicon)
- DaVinci Resolve Studio 20.x
- Python 3.10–3.12 (3.13+ inkompatibel)
- External Scripting auf "Local" in Resolve-Einstellungen

## Setup

```bash
# Python 3.12 via pyenv
pyenv install 3.12
pyenv local 3.12

# Dependencies
pip install -r requirements.txt

# Resolve muss laufen, dann:
python src/server.py
```

## MCP-Integration in Claude Code

```bash
claude mcp add davinci-resolve --scope local -- python3 src/server.py
```

Oder via `.mcp.json` im Projektordner (bereits enthalten).

## Architektur

- **Compound-Tools**: Wenige Tools mit `action`-Parameter
- **Lazy Connection**: Server startet sofort, verbindet erst beim ersten Tool-Call
- **Reconnect-Logik**: Automatischer Reconnect bei Resolve-Neustart
- **FastMCP**: Offizielles Python MCP SDK
