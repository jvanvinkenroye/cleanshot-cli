# cleanshot-cli

Kommandozeile für [CleanShot X](https://cleanshot.com) auf macOS, in Python.
Neuschreibung des Go-Werkzeugs
[XiaofengXie16/cleanshot-cli](https://github.com/XiaofengXie16/cleanshot-cli).

Jeder Befehl wird in eine `cleanshot://`-URL übersetzt und per `open` an die App
übergeben. CleanShot X muss installiert sein. Das URL-Schema meldet nicht zurück,
ob die Aktion geklappt hat. Die Ausgabe sagt deshalb nur „übergeben“.

## Installation

```bash
uv tool install .          # stellt den Befehl `cleanshot-cli` bereit
# oder im Projekt:
uv sync && uv run cleanshot-cli --help
```

## Befehle

| Befehl | URL-Befehl | Optionen |
| --- | --- | --- |
| `capture-area` | `capture-area` | `-a`, `-d`, `--x --y --width --height` |
| `capture-fullscreen` | `capture-fullscreen` | `-a`, `-d` |
| `capture-window` | `capture-window` | `-a` |
| `capture-previous-area` | `capture-previous-area` | `-a` |
| `self-timer` | `self-timer` | `-a`, `-d` |
| `scrolling-capture` | `scrolling-capture` | `-a` |
| `record-screen` | `record-screen` | `-d`, `--x --y --width --height` |
| `capture-text` | `capture-text` | `-f` |
| `annotate` | `open-annotate` | `-f` |
| `pin` | `pin` | `-f` |
| `settings` | `open-settings` | `-t` |
| `annotate-clipboard` | `open-from-clipboard` | |
| `all-in-one` | `all-in-one` | |
| `history` | `open-history` | |
| `restore` | `restore-recently-closed` | |
| `toggle-desktop-icons` / `hide-…` / `show-…` | gleichnamig | |
| `quick-access` | `add-quick-access-overlay` | |

Optionen:

- `-a, --action`: `copy`, `save`, `annotate`, `upload`, `pin`
- `-d, --display`: Bildschirm, ab 1
- `--x --y --width --height`: nur alle vier zusammen; `0` ist eine gültige Koordinate
- `-f, --file`: Bilddatei, muss existieren, wird zum absoluten Pfad

Globale Optionen (vor dem Befehl): `-v/--verbose` gibt die URL aus,
`-q/--quiet` unterdrückt die Ausgabe, `-n/--dry-run` gibt nur die URL aus und ruft
nichts auf, `--version`.

```bash
cleanshot-cli capture-fullscreen -a copy
cleanshot-cli capture-area --x 0 --y 0 --width 800 --height 600 -a upload
cleanshot-cli -n capture-text -f "$HOME/Desktop/Bild mit Leerzeichen.png"
cleanshot-cli settings -t shortcuts
```

## MCP-Server

`cleanshot-cli mcp` startet einen MCP-Server über stdio. Dafür braucht es das
optionale Extra `mcp`:

```bash
uv tool install '.[mcp]'
claude mcp add cleanshot -- cleanshot-cli mcp
```

Ohne Installation, direkt aus dem Projekt:

```bash
claude mcp add cleanshot -- uv --directory ~/src_own/cleanshot-cli run --extra mcp cleanshot-cli mcp
```

Für Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cleanshot": { "command": "cleanshot-cli", "args": ["mcp"] }
  }
}
```

| Werkzeug | Zweck |
| --- | --- |
| `capture` | Aufnahme starten (`mode`: area, fullscreen, window, previous_area, self_timer, scrolling) |
| `capture_image` | Aufnehmen, speichern und das Bild an den Client zurückgeben |
| `latest_capture` | Neueste Aufnahme aus dem Speicherordner zurückgeben |
| `record_screen` | Bildschirmvideo starten |
| `capture_text` | OCR, Ergebnis landet in der Zwischenablage |
| `annotate`, `pin` | Editor öffnen bzw. Bild anheften, optional mit Datei |
| `open_settings` | Einstellungen öffnen |
| `run_simple` | Befehle ohne Parameter (history, restore, Schreibtischsymbole, …) |

Nur `capture_image` und `latest_capture` liefern ein Bild. Alle anderen Werkzeuge
melden nur, dass der Befehl übergeben wurde. Bei `area`, `window` und `scrolling`
muss ein Mensch am Bildschirm auswählen.

Den Speicherordner liest der Server aus den CleanShot-Einstellungen
(`defaults read pl.maketheweb.cleanshotx exportPath`). Mit `CLEANSHOT_EXPORT_DIR`
lässt er sich überschreiben, Rückfall ist `~/Desktop`. Bilder mit einer Kante über
1568 px werden vor der Rückgabe per `sips` verkleinert.

## Unterschiede zur Go-Vorlage

- `x=0` / `y=0` gehen nicht mehr verloren.
- Leerzeichen werden als `%20` statt `+` kodiert.
- Ungültige Werte für `--action`/`--display`, unvollständige Bereiche und
  fehlende Dateien werden abgelehnt, bevor CleanShot aufgerufen wird.
- Erfolgsmeldungen versprechen nichts, was das URL-Schema nicht bestätigt.
- `--version`, `--dry-run`, `--verbose`, `--quiet` und Tests sind neu.
- `pin` nimmt zusätzlich `--file`.

## Entwicklung

```bash
uv sync --extra mcp
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Die Tests ersetzen `subprocess.run` per autouse-Fixture und rufen CleanShot nie
wirklich auf.

## Lizenz

MIT, siehe [LICENSE](LICENSE). CleanShot X ist ein kommerzielles Produkt von
MakeTheWeb; dieses Projekt steht in keiner Verbindung dazu.
