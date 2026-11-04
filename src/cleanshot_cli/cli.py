"""Typer-Oberflaeche: uebersetzt Unterbefehle und Optionen in cleanshot://-URLs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from cleanshot_cli import __version__
from cleanshot_cli.urlscheme import CleanShotError, ParamValue, build_url, open_url

app = typer.Typer(
    name="cleanshot",
    help=(
        "Steuert CleanShot X vom Terminal aus. CleanShot X muss installiert sein; "
        "jeder Befehl wird als cleanshot://-URL an die App uebergeben."
    ),
    no_args_is_help=True,
    add_completion=False,
)


class Action(StrEnum):
    """Was CleanShot nach der Aufnahme mit dem Bild tut."""

    COPY = "copy"
    SAVE = "save"
    ANNOTATE = "annotate"
    UPLOAD = "upload"
    PIN = "pin"


@dataclass(frozen=True)
class Settings:
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False


ActionOpt = Annotated[
    Action | None,
    typer.Option("--action", "-a", help="Aktion nach der Aufnahme."),
]
DisplayOpt = Annotated[
    int | None,
    typer.Option("--display", "-d", min=1, help="Bildschirm (1 = Hauptbildschirm)."),
]
XOpt = Annotated[int | None, typer.Option("--x", min=0, help="X-Koordinate.")]
YOpt = Annotated[int | None, typer.Option("--y", min=0, help="Y-Koordinate.")]
WidthOpt = Annotated[int | None, typer.Option("--width", min=1, help="Breite.")]
HeightOpt = Annotated[int | None, typer.Option("--height", min=1, help="Hoehe.")]
FileOpt = Annotated[
    Path | None,
    typer.Option(
        "--file",
        "-f",
        exists=True,
        dir_okay=False,
        resolve_path=True,
        help="Bilddatei statt Bildschirmauswahl.",
    ),
]


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"cleanshot {__version__}")
        raise typer.Exit


@app.callback()
def root(
    ctx: typer.Context,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Erzeugte URL ausgeben.")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Keine Ausgabe ausser Fehlern.")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Nur die URL ausgeben, CleanShot nicht aufrufen."
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Version ausgeben und beenden.",
        ),
    ] = False,
) -> None:
    if verbose and quiet:
        raise typer.BadParameter("--verbose und --quiet schliessen sich aus.")
    ctx.obj = Settings(verbose=verbose, quiet=quiet, dry_run=dry_run)


def _send(ctx: typer.Context, command: str, params: dict[str, ParamValue]) -> None:
    settings: Settings = ctx.obj or Settings()
    url = build_url(command, params)
    if settings.dry_run:
        typer.echo(url)
        return
    if settings.verbose:
        typer.echo(url, err=True)
    try:
        open_url(url)
    except CleanShotError as exc:
        typer.echo(f"Fehler: {exc}", err=True)
        raise typer.Exit(1) from exc
    if not settings.quiet:
        # Bewusst nur "uebergeben": ob CleanShot die Aktion ausfuehrt, meldet das
        # URL-Schema nicht zurueck.
        typer.echo(f"An CleanShot X uebergeben: {command}")


def _region(
    x: int | None, y: int | None, width: int | None, height: int | None
) -> dict[str, ParamValue]:
    values = {"x": x, "y": y, "width": width, "height": height}
    given = [k for k, v in values.items() if v is not None]
    # Ein halber Bereich ergibt fuer CleanShot keinen Sinn und wuerde still
    # ignoriert; lieber frueh und deutlich abbrechen.
    if given and len(given) != len(values):
        missing = ", ".join(f"--{k}" for k in values if k not in given)
        raise typer.BadParameter(f"Bereich unvollstaendig, es fehlt: {missing}")
    return dict(values)


def _action(action: Action | None) -> str | None:
    return action.value if action else None


# --- Aufnahme -------------------------------------------------------------------


@app.command("capture-area")
def capture_area(
    ctx: typer.Context,
    action: ActionOpt = None,
    display: DisplayOpt = None,
    x: XOpt = None,
    y: YOpt = None,
    width: WidthOpt = None,
    height: HeightOpt = None,
) -> None:
    """Bereich auswaehlen, optional mit vorgegebenem Rechteck."""
    params: dict[str, ParamValue] = {"action": _action(action), "display": display}
    params |= _region(x, y, width, height)
    _send(ctx, "capture-area", params)


@app.command("capture-fullscreen")
def capture_fullscreen(
    ctx: typer.Context, action: ActionOpt = None, display: DisplayOpt = None
) -> None:
    """Ganzen Bildschirm aufnehmen."""
    _send(ctx, "capture-fullscreen", {"action": _action(action), "display": display})


@app.command("capture-window")
def capture_window(ctx: typer.Context, action: ActionOpt = None) -> None:
    """Fenster auswaehlen und aufnehmen."""
    _send(ctx, "capture-window", {"action": _action(action)})


@app.command("capture-previous-area")
def capture_previous_area(ctx: typer.Context, action: ActionOpt = None) -> None:
    """Den zuletzt gewaehlten Bereich erneut aufnehmen."""
    _send(ctx, "capture-previous-area", {"action": _action(action)})


@app.command("self-timer")
def self_timer(
    ctx: typer.Context, action: ActionOpt = None, display: DisplayOpt = None
) -> None:
    """Aufnahme mit Countdown."""
    _send(ctx, "self-timer", {"action": _action(action), "display": display})


@app.command("scrolling-capture")
def scrolling_capture(ctx: typer.Context, action: ActionOpt = None) -> None:
    """Scrollenden Inhalt aufnehmen."""
    _send(ctx, "scrolling-capture", {"action": _action(action)})


@app.command("record-screen")
def record_screen(
    ctx: typer.Context,
    display: DisplayOpt = None,
    x: XOpt = None,
    y: YOpt = None,
    width: WidthOpt = None,
    height: HeightOpt = None,
) -> None:
    """Bildschirmaufnahme starten, optional mit vorgegebenem Rechteck."""
    params: dict[str, ParamValue] = {"display": display}
    params |= _region(x, y, width, height)
    _send(ctx, "record-screen", params)


@app.command("capture-text")
def capture_text(ctx: typer.Context, file: FileOpt = None) -> None:
    """Text per OCR erkennen, vom Bildschirm oder aus einer Bilddatei."""
    _send(ctx, "capture-text", {"filepath": str(file) if file else None})


# --- Bearbeiten -----------------------------------------------------------------


@app.command("annotate")
def annotate(ctx: typer.Context, file: FileOpt = None) -> None:
    """Annotationseditor oeffnen, optional mit einer Bilddatei."""
    _send(ctx, "open-annotate", {"filepath": str(file) if file else None})


@app.command("pin")
def pin(ctx: typer.Context, file: FileOpt = None) -> None:
    """Bild als schwebendes Fenster anheften."""
    _send(ctx, "pin", {"filepath": str(file) if file else None})


@app.command("settings")
def settings(
    ctx: typer.Context,
    tab: Annotated[
        str | None,
        typer.Option("--tab", "-t", help="Reiter, z. B. general, shortcuts, cloud."),
    ] = None,
) -> None:
    """Einstellungen von CleanShot X oeffnen."""
    _send(ctx, "open-settings", {"tab": tab})


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


def _register_simple(name: str, url_command: str, help_text: str) -> None:
    def command(ctx: typer.Context) -> None:
        _send(ctx, url_command, {})

    app.command(name, help=help_text)(command)


for _name, _url_command, _help in SIMPLE_COMMANDS:
    _register_simple(_name, _url_command, _help)


def main() -> None:
    app()
