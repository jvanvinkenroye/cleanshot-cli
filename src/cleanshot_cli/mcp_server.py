"""MCP-Server: stellt die CleanShot-Befehle einem KI-Client zur Verfuegung.

Laeuft ueber stdio. Deshalb schreibt hier nichts nach stdout - jede Zeile dort
wuerde das Protokoll zerstoeren.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

import anyio.to_thread
from mcp.server import MCPServer
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError

from cleanshot_cli.captures import export_dir, image_bytes, newest_image
from cleanshot_cli.captures import wait_for_new_image as _wait
from cleanshot_cli.commands import (
    SIMPLE_COMMANDS,
    Action,
    CaptureMode,
    capture_params,
    region,
)
from cleanshot_cli.urlscheme import CleanShotError, ParamValue, build_url, open_url

server = MCPServer(
    "cleanshot-cli",
    instructions=(
        "Steuert CleanShot X auf dem Mac des Nutzers. Aufnahmen in den Modi "
        "area, window und scrolling brauchen eine Auswahl durch den Menschen am "
        "Bildschirm. Um ein Bild selbst anzusehen, capture_image oder "
        "latest_capture verwenden; die uebrigen Werkzeuge melden nur, dass der "
        "Befehl an CleanShot uebergeben wurde."
    ),
)

SimpleName = Literal[
    "annotate-clipboard",
    "all-in-one",
    "history",
    "restore",
    "toggle-desktop-icons",
    "hide-desktop-icons",
    "show-desktop-icons",
    "quick-access",
]
_SIMPLE = {name: url_command for name, url_command, _ in SIMPLE_COMMANDS}


def _send(command: str, params: dict[str, ParamValue]) -> str:
    url = build_url(command, params)
    try:
        open_url(url)
    except CleanShotError as exc:
        raise ToolError(str(exc)) from exc
    return f"An CleanShot X uebergeben: {url}"


def _checked_file(file: str | None) -> str | None:
    """Loest einen Dateipfad auf und prueft ihn, bevor er in die URL geht."""
    if file is None:
        return None
    path = Path(file).expanduser().resolve()
    if not path.is_file():
        raise ToolError(f"Datei nicht gefunden: {path}")
    return str(path)


def _params(
    mode: str, **kwargs: int | Action | None
) -> tuple[str, dict[str, ParamValue]]:
    try:
        return capture_params(mode, **kwargs)  # type: ignore[arg-type]
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@server.tool()
def capture(
    mode: CaptureMode,
    action: Action | None = None,
    display: int | None = None,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """Startet eine Bildschirmaufnahme in CleanShot X.

    mode: area (Bereich), fullscreen, window, previous_area (letzter Bereich),
    self_timer, scrolling. area/window/scrolling verlangen eine Auswahl durch
    den Menschen. display (ab 1) nur bei area, fullscreen, self_timer. Bereich
    x/y/width/height nur bei area und nur alle vier zusammen. Das Bild kommt
    nicht zurueck - dafuer capture_image verwenden.
    """
    command, params = _params(
        mode, action=action, display=display, x=x, y=y, width=width, height=height
    )
    return _send(command, params)


@server.tool()
async def capture_image(
    mode: CaptureMode = "fullscreen",
    display: int | None = None,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
    timeout: float = 60.0,
) -> list[Image | str]:
    """Nimmt auf, speichert und gibt das Bild zurueck.

    Wie capture, aber mit action=save; wartet bis zu timeout Sekunden auf die
    neue Datei im CleanShot-Speicherordner und liefert sie (verkleinert) als
    Bild plus Pfad. Bei area/window/scrolling muss der Mensch auswaehlen.
    """
    if not 1 <= timeout <= 600:
        raise ToolError("timeout muss zwischen 1 und 600 Sekunden liegen.")
    command, params = _params(
        mode,
        action=Action.SAVE,
        display=display,
        x=x,
        y=y,
        width=width,
        height=height,
    )
    directory = export_dir()
    # Eine Sekunde Puffer: mtime-Aufloesung und Uhrabweichung duerfen die eben
    # entstandene Datei nicht ausschliessen.
    since = time.time() - 1
    _send(command, params)
    try:
        path = await anyio.to_thread.run_sync(_wait, directory, since, timeout)
    except TimeoutError as exc:
        raise ToolError(str(exc)) from exc
    return await _image_result(path)


@server.tool()
async def latest_capture() -> list[Image | str]:
    """Gibt die neueste Aufnahme aus dem CleanShot-Speicherordner zurueck."""
    directory = export_dir()
    path = newest_image(directory)
    if path is None:
        raise ToolError(f"Keine Bilder in {directory}.")
    return await _image_result(path)


async def _image_result(path: Path) -> list[Image | str]:
    data, fmt = await anyio.to_thread.run_sync(image_bytes, path)
    return [Image(data=data, format=fmt), f"Datei: {path}"]


@server.tool()
def record_screen(
    display: int | None = None,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """Startet die Bildschirmaufnahme (Video), optional mit Bereich."""
    if display is not None and display < 1:
        raise ToolError("display muss mindestens 1 sein.")
    try:
        params: dict[str, ParamValue] = {"display": display}
        params |= region(x, y, width, height)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return _send("record-screen", params)


@server.tool()
def capture_text(file: str | None = None) -> str:
    """Texterkennung (OCR): ohne file waehlt der Mensch einen Bereich.

    Der erkannte Text landet in der Zwischenablage, nicht in der Antwort.
    """
    return _send("capture-text", {"filepath": _checked_file(file)})


@server.tool()
def annotate(file: str | None = None) -> str:
    """Oeffnet den Annotationseditor, optional mit einer Bilddatei."""
    return _send("open-annotate", {"filepath": _checked_file(file)})


@server.tool()
def pin(file: str | None = None) -> str:
    """Heftet ein Bild als schwebendes Fenster an den Bildschirm."""
    return _send("pin", {"filepath": _checked_file(file)})


@server.tool()
def open_settings(tab: str | None = None) -> str:
    """Oeffnet die Einstellungen, optional einen Reiter (general, shortcuts, ...)."""
    return _send("open-settings", {"tab": tab})


@server.tool()
def run_simple(name: SimpleName) -> str:
    """Einfache Befehle ohne Parameter.

    annotate-clipboard, all-in-one, history, restore (zuletzt geschlossene
    Aufnahme), toggle-/hide-/show-desktop-icons, quick-access.
    """
    return _send(_SIMPLE[name], {})
