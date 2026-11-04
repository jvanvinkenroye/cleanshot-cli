"""Gemeinsame Fixtures.

Kein Test darf das echte ``open`` aufrufen - sonst loest der Testlauf
Screenshots, Bildschirmaufnahmen oder ausgeblendete Schreibtischsymbole aus.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class FakeRun:
    returncode: int = 0
    stderr: str = ""
    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        return subprocess.CompletedProcess(args, self.returncode, "", self.stderr)

    @property
    def urls(self) -> list[str]:
        return [call[-1] for call in self.calls]


@pytest.fixture(autouse=True)
def fake_run(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRun]:
    fake = FakeRun()
    monkeypatch.setattr("cleanshot_cli.urlscheme.subprocess.run", fake)
    monkeypatch.setattr(
        "cleanshot_cli.urlscheme.shutil.which", lambda _: "/usr/bin/open"
    )
    yield fake
