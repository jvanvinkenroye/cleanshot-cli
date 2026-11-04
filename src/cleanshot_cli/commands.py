"""Befehlswissen, das Kommandozeile und MCP-Server teilen.

Beide Oberflaechen sollen dieselben URL-Befehle mit denselben Regeln erzeugen;
deshalb liegt hier, was sonst doppelt gepflegt wuerde.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from cleanshot_cli.urlscheme import ParamValue


class Action(StrEnum):
    """Was CleanShot nach der Aufnahme mit dem Bild tut."""

    COPY = "copy"
    SAVE = "save"
    ANNOTATE = "annotate"
    UPLOAD = "upload"
    PIN = "pin"


CaptureMode = Literal[
    "area", "fullscreen", "window", "previous_area", "self_timer", "scrolling"
]

# Aufnahmeart -> (URL-Befehl, nimmt display, nimmt Bereich)
CAPTURE_MODES: dict[str, tuple[str, bool, bool]] = {
    "area": ("capture-area", True, True),
    "fullscreen": ("capture-fullscreen", True, False),
    "window": ("capture-window", False, False),
    "previous_area": ("capture-previous-area", False, False),
    "self_timer": ("self-timer", True, False),
    "scrolling": ("scrolling-capture", False, False),
}

# Befehle ohne Optionen: Name auf der Kommandozeile -> URL-Befehl, Hilfetext.
SIMPLE_COMMANDS: tuple[tuple[str, str, str], ...] = (
    (
        "annotate-clipboard",
        "open-from-clipboard",
        "Bild aus der Zwischenablage annotieren.",
    ),
    ("all-in-one", "all-in-one", "All-in-One-Modus starten."),
    ("history", "open-history", "Verlauf oeffnen."),
    (
        "restore",
        "restore-recently-closed",
        "Zuletzt geschlossene Aufnahme zurueckholen.",
    ),
    ("toggle-desktop-icons", "toggle-desktop-icons", "Schreibtischsymbole umschalten."),
    ("hide-desktop-icons", "hide-desktop-icons", "Schreibtischsymbole ausblenden."),
    ("show-desktop-icons", "show-desktop-icons", "Schreibtischsymbole einblenden."),
    ("quick-access", "add-quick-access-overlay", "Quick-Access-Overlay hinzufuegen."),
)


def region(
    x: int | None, y: int | None, width: int | None, height: int | None
) -> dict[str, ParamValue]:
    """Prueft einen Aufnahmebereich: entweder alle vier Werte oder keiner.

    Ein halber Bereich ergibt fuer CleanShot keinen Sinn und wuerde still
    ignoriert; lieber frueh und deutlich abbrechen.
    """
    values: dict[str, ParamValue] = {"x": x, "y": y, "width": width, "height": height}
    given = [k for k, v in values.items() if v is not None]
    if given and len(given) != len(values):
        missing = ", ".join(k for k in values if k not in given)
        raise ValueError(f"Bereich unvollstaendig, es fehlt: {missing}")
    if x is not None and y is not None and (x < 0 or y < 0):
        raise ValueError("x und y duerfen nicht negativ sein.")
    if width is not None and height is not None and (width < 1 or height < 1):
        raise ValueError("width und height muessen mindestens 1 sein.")
    return values


def capture_params(
    mode: str,
    action: Action | None = None,
    display: int | None = None,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> tuple[str, dict[str, ParamValue]]:
    """Liefert URL-Befehl und Parameter fuer eine Aufnahmeart."""
    try:
        command, takes_display, takes_region = CAPTURE_MODES[mode]
    except KeyError:
        raise ValueError(f"Unbekannte Aufnahmeart: {mode}") from None
    if display is not None and not takes_display:
        raise ValueError(f"Aufnahmeart {mode} kennt keinen Bildschirm.")
    if display is not None and display < 1:
        raise ValueError("display muss mindestens 1 sein.")
    if not takes_region and any(v is not None for v in (x, y, width, height)):
        raise ValueError(f"Aufnahmeart {mode} kennt keinen Bereich.")
    params: dict[str, ParamValue] = {
        "action": action.value if action else None,
        "display": display,
    }
    params |= region(x, y, width, height)
    return command, params
