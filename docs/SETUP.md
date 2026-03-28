# Setup-Anleitung

## Voraussetzungen

1. **macOS** mit Apple Silicon
2. **DaVinci Resolve Studio** 20.x installiert
3. **Python 3.10–3.12** (via pyenv empfohlen)

## Resolve-Einstellung

1. DaVinci Resolve öffnen
2. Preferences > General > External scripting using → **"Local"**
3. Resolve neu starten

## Installation

```bash
cd ~/Projects/davinci-resolve-mcp
pyenv local 3.12
pip install -r requirements.txt
```

## Server starten

```bash
python src/server.py
```

## In Claude Code registrieren

```bash
claude mcp add davinci-resolve --scope local -- python3 src/server.py
```
