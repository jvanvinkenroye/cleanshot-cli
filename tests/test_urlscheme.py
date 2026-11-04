from __future__ import annotations

import pytest

from cleanshot_cli.urlscheme import CleanShotError, build_url, open_url
from tests.conftest import FakeRun


@pytest.mark.parametrize(
    ("command", "params", "expected"),
    [
        ("pin", None, "cleanshot://pin"),
        ("pin", {}, "cleanshot://pin"),
        ("pin", {"filepath": None}, "cleanshot://pin"),
        ("capture-area", {"x": 0, "y": 0}, "cleanshot://capture-area?x=0&y=0"),
        (
            "open-annotate",
            {"filepath": "/Users/me/My Shots/a+b.png"},
            "cleanshot://open-annotate?filepath=%2FUsers%2Fme%2FMy%20Shots%2Fa%2Bb.png",
        ),
        ("x", {"tab": "a&b=c"}, "cleanshot://x?tab=a%26b%3Dc"),
    ],
)
def test_build_url(
    command: str, params: dict[str, str | int | None] | None, expected: str
) -> None:
    assert build_url(command, params) == expected


def test_open_url_calls_open(fake_run: FakeRun) -> None:
    open_url("cleanshot://pin")
    assert fake_run.calls == [["/usr/bin/open", "cleanshot://pin"]]


def test_open_url_reports_failure(fake_run: FakeRun) -> None:
    fake_run.returncode = 1
    fake_run.stderr = "No application knows how to open URL"
    with pytest.raises(CleanShotError, match="No application"):
        open_url("cleanshot://pin")


def test_open_url_without_open_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cleanshot_cli.urlscheme.shutil.which", lambda _: None)
    with pytest.raises(CleanShotError, match="macOS"):
        open_url("cleanshot://pin")
