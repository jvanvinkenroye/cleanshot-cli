from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from cleanshot_cli import captures
from tests.conftest import REAL_RUN, FakeRun


def write_png(path: Path, width: int, height: int) -> Path:
    """Minimales, gueltiges PNG ohne Bildbibliothek."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(b"\x00" + b"\xff" * (width * 3) for _ in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return path


def touch(path: Path, mtime: float) -> Path:
    path.write_bytes(b"x")
    os.utime(path, (mtime, mtime))
    return path


def test_export_dir_prefers_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run: FakeRun
) -> None:
    monkeypatch.setenv("CLEANSHOT_EXPORT_DIR", str(tmp_path))
    assert captures.export_dir() == tmp_path
    assert fake_run.calls == []


def test_export_dir_reads_cleanshot_prefs(fake_run: FakeRun) -> None:
    fake_run.stdout = "/Users/me/ScreenShots\n"
    assert captures.export_dir() == Path("/Users/me/ScreenShots")
    assert fake_run.calls[0][1:] == ["read", captures.PREFS_DOMAIN, "exportPath"]


def test_export_dir_falls_back_to_desktop(fake_run: FakeRun) -> None:
    fake_run.returncode = 1
    assert captures.export_dir() == Path.home() / "Desktop"


def test_newest_image(tmp_path: Path) -> None:
    touch(tmp_path / "alt.png", 1000)
    neu = touch(tmp_path / "neu.jpg", 2000)
    touch(tmp_path / "neuer.txt", 3000)
    assert captures.newest_image(tmp_path) == neu
    assert captures.newest_image(tmp_path, since=2500) is None
    assert captures.newest_image(tmp_path / "fehlt") is None


def test_wait_for_new_image_finds_file(tmp_path: Path) -> None:
    neu = touch(tmp_path / "shot.png", 5000)
    assert captures.wait_for_new_image(tmp_path, 4000, 2, interval=0.01) == neu


def test_wait_for_new_image_times_out(tmp_path: Path) -> None:
    touch(tmp_path / "alt.png", 1000)
    with pytest.raises(TimeoutError, match="CLEANSHOT_EXPORT_DIR"):
        captures.wait_for_new_image(tmp_path, 4000, 0.05, interval=0.01)


def test_image_bytes_without_sips(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    image = write_png(tmp_path / "a.png", 2, 2)
    assert captures.image_bytes(image) == (image.read_bytes(), "png")


needs_sips = pytest.mark.skipif(
    sys.platform != "darwin" or not Path("/usr/bin/sips").exists(),
    reason="sips gibt es nur auf macOS",
)


@needs_sips
@pytest.mark.parametrize(("width", "expected_width"), [(3000, 1568), (200, 200)])
def test_image_bytes_shrinks_only_large_images(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, width: int, expected_width: int
) -> None:
    monkeypatch.setattr(subprocess, "run", REAL_RUN)
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    image = write_png(tmp_path / "a.png", width, 10)
    data, fmt = captures.image_bytes(image)
    assert fmt == "png"
    # Breite steht im IHDR-Chunk ab Byte 16.
    assert struct.unpack(">I", data[16:20])[0] == expected_width
    assert shutil.which("sips")
