"""Gespeicherte Aufnahmen finden und fuer die Rueckgabe aufbereiten.

Das URL-Schema meldet keine Ergebnisdatei. Der einzige Weg an das Bild ist,
nach der Aufnahme im Speicherordner von CleanShot nach einer neuen Datei zu
suchen.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

PREFS_DOMAIN = "pl.maketheweb.cleanshotx"
ENV_EXPORT_DIR = "CLEANSHOT_EXPORT_DIR"
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".heic", ".gif", ".webp"})
# Lange Kante, die gaengige Clients ohne eigenes Verkleinern verarbeiten; ein
# Retina-Vollbild hat sonst schnell mehrere MB Base64.
MAX_EDGE = 1568


def export_dir() -> Path:
    """Speicherordner: Umgebungsvariable, dann CleanShot-Einstellung, dann Desktop."""
    if env := os.environ.get(ENV_EXPORT_DIR):
        return Path(env).expanduser()
    defaults_bin = shutil.which("defaults")
    if defaults_bin:
        result = subprocess.run(
            [defaults_bin, "read", PREFS_DOMAIN, "exportPath"],
            capture_output=True,
            text=True,
            check=False,
        )
        value = (result.stdout or "").strip()
        if result.returncode == 0 and value:
            return Path(value).expanduser()
    return Path.home() / "Desktop"


def newest_image(directory: Path, since: float | None = None) -> Path | None:
    """Neueste Bilddatei im Ordner, optional nur juenger als ``since``."""
    if not directory.is_dir():
        return None
    candidates = [
        (p.stat().st_mtime, p)
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    ]
    if since is not None:
        candidates = [(m, p) for m, p in candidates if m >= since]
    if not candidates:
        return None
    return max(candidates)[1]


def wait_for_new_image(
    directory: Path, since: float, timeout: float, interval: float = 0.3
) -> Path:
    """Wartet auf eine neue, fertig geschriebene Bilddatei.

    CleanShot schreibt nicht atomar; erst wenn die Groesse zweimal hintereinander
    gleich und nicht null ist, gilt die Datei als fertig.
    """
    deadline = time.monotonic() + timeout
    last: tuple[Path, int] | None = None
    while time.monotonic() < deadline:
        found = newest_image(directory, since)
        if found is not None:
            size = found.stat().st_size
            if size > 0 and last == (found, size):
                return found
            last = (found, size)
        time.sleep(interval)
    raise TimeoutError(
        f"Keine neue Aufnahme in {directory} nach {timeout:.0f} s. "
        "Abgebrochen, oder speichert CleanShot woanders? "
        f"Ordner per {ENV_EXPORT_DIR} setzen."
    )


def image_bytes(path: Path, max_edge: int = MAX_EDGE) -> tuple[bytes, str]:
    """Liest ein Bild, bei Bedarf per macOS-``sips`` verkleinert.

    Gibt Bytes und Format (``png``/``jpeg``) zurueck. ``sips`` statt Pillow, weil
    es auf jedem Mac vorhanden ist und das Paket schlank bleibt.
    """
    sips = shutil.which("sips")
    fmt = _format(path)
    if sips is None:
        return path.read_bytes(), fmt
    size = _pixel_size(sips, path)
    too_large = size is None or max(size) > max_edge
    if not too_large and fmt in {"png", "jpeg", "gif", "webp"}:
        return path.read_bytes(), fmt
    args = ["-s", "format", "png"]
    # -Z vergroessert auch kleine Bilder; deshalb nur anwenden, wenn noetig.
    if too_large:
        args = ["-Z", str(max_edge), *args]
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "bild.png"
        result = subprocess.run(
            [sips, *args, str(path), "--out", str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not target.exists():
            return path.read_bytes(), fmt
        return target.read_bytes(), "png"


def _pixel_size(sips: str, path: Path) -> tuple[int, int] | None:
    result = subprocess.run(
        [sips, "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    values: dict[str, int] = {}
    for line in result.stdout.splitlines():
        key, _, value = line.strip().partition(":")
        if key in {"pixelWidth", "pixelHeight"} and value.strip().isdigit():
            values[key] = int(value)
    if len(values) != 2:
        return None
    return values["pixelWidth"], values["pixelHeight"]


def _format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return "jpeg" if suffix == "jpg" else suffix
