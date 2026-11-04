from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cleanshot_cli import __version__
from cleanshot_cli.cli import app
from cleanshot_cli.commands import SIMPLE_COMMANDS
from tests.conftest import FakeRun

runner = CliRunner()


@pytest.mark.parametrize(
    ("args", "url"),
    [
        (["capture-fullscreen"], "cleanshot://capture-fullscreen"),
        (
            ["capture-fullscreen", "--action", "copy", "--display", "2"],
            "cleanshot://capture-fullscreen?action=copy&display=2",
        ),
        (
            [
                "capture-area",
                "--x",
                "0",
                "--y",
                "0",
                "--width",
                "800",
                "--height",
                "600",
            ],
            "cleanshot://capture-area?x=0&y=0&width=800&height=600",
        ),
        (
            [
                "record-screen",
                "-d",
                "1",
                "--x",
                "10",
                "--y",
                "20",
                "--width",
                "5",
                "--height",
                "6",
            ],
            "cleanshot://record-screen?display=1&x=10&y=20&width=5&height=6",
        ),
        (["capture-window", "-a", "pin"], "cleanshot://capture-window?action=pin"),
        (["settings", "--tab", "shortcuts"], "cleanshot://open-settings?tab=shortcuts"),
        (["annotate"], "cleanshot://open-annotate"),
    ],
)
def test_command_builds_url(fake_run: FakeRun, args: list[str], url: str) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert fake_run.urls == [url]


@pytest.mark.parametrize(("name", "url_command", "_help"), SIMPLE_COMMANDS)
def test_simple_commands(
    fake_run: FakeRun, name: str, url_command: str, _help: str
) -> None:
    result = runner.invoke(app, [name])
    assert result.exit_code == 0, result.output
    assert fake_run.urls == [f"cleanshot://{url_command}"]


@pytest.mark.parametrize("command", ["capture-text", "annotate", "pin"])
def test_file_option_uses_absolute_path(
    fake_run: FakeRun,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    image = tmp_path / "mit leerzeichen.png"
    image.write_bytes(b"")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [command, "--file", image.name])
    assert result.exit_code == 0, result.output
    assert fake_run.urls[0].endswith("mit%20leerzeichen.png")
    assert "%2F" in fake_run.urls[0]  # absoluter Pfad


def test_missing_file_is_rejected(fake_run: FakeRun) -> None:
    result = runner.invoke(app, ["annotate", "--file", "/gibt/es/nicht.png"])
    assert result.exit_code == 2
    assert fake_run.calls == []


def test_incomplete_region_is_rejected(fake_run: FakeRun) -> None:
    result = runner.invoke(app, ["capture-area", "--x", "5"])
    assert result.exit_code == 2
    assert "width" in result.output
    assert fake_run.calls == []


@pytest.mark.parametrize(
    "args",
    [
        ["capture-area", "--action", "delete"],
        ["capture-fullscreen", "--display", "0"],
        ["capture-area", "--x", "-1", "--y", "0", "--width", "1", "--height", "1"],
    ],
)
def test_invalid_values_are_rejected(fake_run: FakeRun, args: list[str]) -> None:
    assert runner.invoke(app, args).exit_code == 2
    assert fake_run.calls == []


def test_dry_run_prints_url_only(fake_run: FakeRun) -> None:
    result = runner.invoke(app, ["--dry-run", "pin"])
    assert result.exit_code == 0
    assert result.output.strip() == "cleanshot://pin"
    assert fake_run.calls == []


def test_quiet_suppresses_output(fake_run: FakeRun) -> None:
    result = runner.invoke(app, ["-q", "history"])
    assert result.exit_code == 0
    assert result.output == ""
    assert fake_run.urls == ["cleanshot://open-history"]


def test_verbose_and_quiet_conflict(fake_run: FakeRun) -> None:
    assert runner.invoke(app, ["-v", "-q", "history"]).exit_code == 2
    assert fake_run.calls == []


def test_open_failure_exits_nonzero(fake_run: FakeRun) -> None:
    fake_run.returncode = 1
    fake_run.stderr = "kaputt"
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 1
    assert "kaputt" in result.output


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output
