import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from soundstage.errors import InputFileError, RenderConfigError
from soundstage.render import render
from soundstage.render.cover import make_fallback_cover, validate_cover_image

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


def test_corrupt_cover_rejected(tmp_path):
    """損毀的封面圖必須在呼叫 ffmpeg 之前擋下來。

    ffmpeg 的 -loop 1 遇到讀不出影格的圖片會無限重試、永不結束，
    放過去的話使用者只會看到程式卡死。
    """
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"fake")
    bad_cover = tmp_path / "cover.jpg"
    bad_cover.write_text("這不是圖片", encoding="utf-8")

    with pytest.raises(InputFileError, match="無法解讀"):
        render(audio, tmp_path / "out.mp4", cover_path=bad_cover)


def test_validate_cover_accepts_real_image(tmp_path):
    cover = make_fallback_cover("ok", tmp_path / "cover.png", width=64, height=64)
    validate_cover_image(cover)  # 不該拋錯


@pytest.mark.parametrize("width,height", [(1921, 1080), (1920, 1081)])
def test_odd_dimensions_rejected(tmp_path, width, height):
    """H.264 的 yuv420p 要求偶數尺寸，奇數要給清楚訊息而不是 ffmpeg 亂碼錯誤。"""
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"fake")

    with pytest.raises(RenderConfigError, match="偶數"):
        render(audio, tmp_path / "out.mp4", width=width, height=height)


def test_scale_filter_forces_even_intermediate():
    from soundstage.render import RenderSpec, build_render_command

    command = build_render_command(
        RenderSpec(
            audio_path=Path("a.wav"),
            cover_path=Path("c.png"),
            output_path=Path("o.mp4"),
        )
    )
    assert "force_divisible_by=2" in command[command.index("-vf") + 1]


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
