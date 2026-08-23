import shutil
import subprocess

import pytest
from PIL import Image

from soundstage.errors import InputFileError
from soundstage.render import render
from soundstage.render.cover import make_fallback_cover

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def test_fallback_cover(tmp_path):
    out = make_fallback_cover("my-song", tmp_path / "cover.png", width=640, height=360)
    with Image.open(out) as image:
        assert image.size == (640, 360)


def test_render_missing_audio(tmp_path):
    with pytest.raises(InputFileError, match="音檔"):
        render(tmp_path / "nope.wav", tmp_path / "out.mp4")


def test_render_missing_cover(tmp_path):
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"fake")
    with pytest.raises(InputFileError, match="封面"):
        render(audio, tmp_path / "out.mp4", cover_path=tmp_path / "nope.jpg")


@pytest.mark.skipif(not HAS_FFMPEG, reason="需要 ffmpeg")
def test_render_end_to_end(tmp_path):
    audio = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(audio)],
        check=True,
    )

    out = render(audio, tmp_path / "tone.mp4", width=320, height=240, fps=2)

    assert out.is_file() and out.stat().st_size > 0
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )
    streams = set(probe.stdout.split())
    assert streams == {"video", "audio"}
