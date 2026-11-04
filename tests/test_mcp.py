from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from cleanshot_cli.mcp_server import server
from tests.conftest import FakeRun
from tests.test_captures import write_png

pytestmark = pytest.mark.anyio


async def call(name: str, args: dict[str, Any] | None = None) -> Any:
    async with Client(server) as client:
        return await client.call_tool(name, args or {})


def text(result: Any) -> str:
    return "\n".join(c.text for c in result.content if c.type == "text")


async def test_tool_list() -> None:
    async with Client(server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
    assert names == {
        "capture",
        "capture_image",
        "latest_capture",
        "record_screen",
        "capture_text",
        "annotate",
        "pin",
        "open_settings",
        "run_simple",
    }


@pytest.mark.parametrize(
    ("args", "url"),
    [
        ({"mode": "fullscreen"}, "cleanshot://capture-fullscreen"),
        (
            {
                "mode": "area",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 20,
                "action": "copy",
            },
            "cleanshot://capture-area?action=copy&x=0&y=0&width=10&height=20",
        ),
        ({"mode": "previous_area"}, "cleanshot://capture-previous-area"),
    ],
)
async def test_capture(fake_run: FakeRun, args: dict[str, Any], url: str) -> None:
    result = await call("capture", args)
    assert not result.is_error, text(result)
    assert fake_run.urls == [url]


@pytest.mark.parametrize(
    "args",
    [
        {"mode": "area", "x": 5},
        {"mode": "window", "display": 2},
        {"mode": "fullscreen", "x": 0, "y": 0, "width": 1, "height": 1},
        {"mode": "fullscreen", "display": 0},
        {"mode": "nonsense"},
        {"mode": "fullscreen", "action": "delete"},
    ],
)
async def test_capture_rejects_bad_input(
    fake_run: FakeRun, args: dict[str, Any]
) -> None:
    result = await call("capture", args)
    assert result.is_error
    assert fake_run.urls == []


async def test_file_must_exist(fake_run: FakeRun) -> None:
    result = await call("annotate", {"file": "/gibt/es/nicht.png"})
    assert result.is_error
    assert "nicht gefunden" in text(result)
    assert fake_run.urls == []


async def test_file_is_resolved(fake_run: FakeRun, tmp_path: Path) -> None:
    image = write_png(tmp_path / "mit leer.png", 1, 1)
    result = await call("pin", {"file": str(image)})
    assert not result.is_error, text(result)
    assert fake_run.urls[0].endswith("mit%20leer.png")


async def test_run_simple(fake_run: FakeRun) -> None:
    result = await call("run_simple", {"name": "history"})
    assert not result.is_error
    assert fake_run.urls == ["cleanshot://open-history"]


async def test_open_failure_is_tool_error(fake_run: FakeRun) -> None:
    fake_run.returncode = 1
    fake_run.stderr = "kaputt"
    result = await call("run_simple", {"name": "history"})
    assert result.is_error
    assert "kaputt" in text(result)


async def test_capture_image_returns_new_file(
    fake_run: FakeRun, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLEANSHOT_EXPORT_DIR", str(tmp_path))
    shot = tmp_path / "CleanShot neu.png"
    fake_run.on_open = lambda _url: write_png(shot, 4, 3)
    result = await call("capture_image", {"mode": "fullscreen", "timeout": 5})
    assert not result.is_error, text(result)
    assert fake_run.urls == ["cleanshot://capture-fullscreen?action=save"]
    images = [c for c in result.content if c.type == "image"]
    assert base64.b64decode(images[0].data) == shot.read_bytes()
    assert str(shot) in text(result)


async def test_capture_image_times_out(
    fake_run: FakeRun, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLEANSHOT_EXPORT_DIR", str(tmp_path))
    result = await call("capture_image", {"mode": "fullscreen", "timeout": 1})
    assert result.is_error
    assert "Keine neue Aufnahme" in text(result)


async def test_latest_capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANSHOT_EXPORT_DIR", str(tmp_path))
    assert (await call("latest_capture")).is_error
    write_png(tmp_path / "a.png", 1, 1)
    result = await call("latest_capture")
    assert not result.is_error
    assert any(c.type == "image" for c in result.content)
