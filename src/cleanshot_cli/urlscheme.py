"""Aufbau und Aufruf von cleanshot://-URLs.

CleanShot X laesst sich ausschliesslich ueber sein URL-Schema fernsteuern. Dieses
Modul kennt keine Kommandozeile, damit es sich ohne Typer testen und
wiederverwenden laesst.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Mapping
from urllib.parse import quote, urlencode

SCHEME = "cleanshot"

ParamValue = str | int | None


class CleanShotError(RuntimeError):
    """CleanShot liess sich nicht aufrufen."""


def build_url(command: str, params: Mapping[str, ParamValue] | None = None) -> str:
    """Setzt eine cleanshot://-URL zusammen.

    Parameter mit ``None`` fallen weg; ``0`` bleibt erhalten, weil x=0 und y=0
    gueltige Koordinaten sind (die Go-Vorlage hat sie verschluckt).
    """
    url = f"{SCHEME}://{command}"
    query = {k: str(v) for k, v in (params or {}).items() if v is not None}
    if query:
        # quote statt quote_plus: Ein "+" fuer Leerzeichen liest CleanShot in
        # Dateipfaden nicht zuverlaessig zurueck, "%20" schon.
        url += "?" + urlencode(query, quote_via=quote)
    return url


def open_url(url: str) -> None:
    """Uebergibt die URL per macOS-``open`` an CleanShot X.

    ``open`` meldet nur, ob die URL zugestellt wurde, nicht ob CleanShot die
    Aktion ausgefuehrt hat. Mehr Rueckmeldung bietet das URL-Schema nicht.
    """
    open_bin = shutil.which("open")
    if open_bin is None:
        raise CleanShotError("'open' nicht gefunden - laeuft das auf macOS?")
    # Argumentliste statt Shell: die URL kann Pfade mit beliebigen Zeichen tragen.
    result = subprocess.run(
        [open_bin, url], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"Exit-Code {result.returncode}"
        raise CleanShotError(
            f"CleanShot X nicht erreichbar ({detail}). Ist die App installiert?"
        )
