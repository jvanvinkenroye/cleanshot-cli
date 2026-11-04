"""Gemeinsame Fixtures.

Kein Test darf das echte ``open`` aufrufen - sonst loest der Testlauf
Screenshots, Bildschirmaufnahmen oder ausgeblendete Schreibtischsymbole aus.
Ersetzt wird ``subprocess.run`` modulweit, damit auch ``defaults`` und ``sips``
nicht unbemerkt die echte Umgebung lesen.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

REAL_RUN = subprocess.run


@dataclass
class FakeRun:
    returncode: int = 0
    stderr: str = ""
    stdout: str = ""
    calls: list[list[str]] = field(default_factory=list)
    # Wird bei jedem open-Aufruf mit der URL aufgerufen, z. B. um eine
    # gespeicherte Aufnahme nachzustellen.
    on_open: Callable[[str], object] | None = None

    def __call__(self, args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        if Path(args[0]).name == "open" and self.on_open is not None:
            self.on_open(args[-1])
        return subprocess.CompletedProcess(
            args, self.returncode, self.stdout, self.stderr
        )

    @property
    def urls(self) -> list[str]:
        return [c[-1] for c in self.calls if Path(c[0]).name == "open"]


@pytest.fixture(autouse=True)
def fake_run(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRun]:
    fake = FakeRun()
    monkeypatch.setattr(subprocess, "run", fake)
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.delenv("CLEANSHOT_EXPORT_DIR", raising=False)
    yield fake


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
