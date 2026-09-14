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


def test_config_error_precedes_ffmpeg_check(tmp_path, monkeypatch):
    """參數驗證不該需要先裝好 ffmpeg。

    順序反過來的話有兩個後果：解析度打錯的人會先被叫去裝 ffmpeg、裝完才
    發現真正的問題；而這類測試會隨執行環境有沒有 ffmpeg 而飄。這裡強制
    模擬「沒有 ffmpeg」來把順序釘死。
    """
    monkeypatch.setattr(shutil, "which", lambda _: None)

    audio = tmp_path / "song.wav"
    audio.write_bytes(b"fake")

    with pytest.raises(RenderConfigError, match="偶數"):
        render(audio, tmp_path / "out.mp4", width=1921, height=1080)


@pytest.mark.skipif(not HAS_FFMPEG, reason="需要 ffmpeg")
def test_output_video_not_longer_than_audio(tmp_path):
    """輸出的影像軌不該比音訊長。

    封面是 -loop 1 的無限長串流，光靠 -shortest 收尾會多出 2 秒左右，
    且 ffmpeg 照樣回報成功——屬於靜默的錯誤輸出，所以用實際輸出驗。
    """
    audio = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(audio)],
        check=True,
    )

    out = render(audio, tmp_path / "tone.mp4", width=320, height=240, fps=10)

    def stream_duration(select: str) -> float:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", select,
             "-show_entries", "stream=duration", "-of", "default=nw=1:nk=1", str(out)],
            capture_output=True, text=True, check=True,
        )
        return float(probe.stdout.strip())

    video, audio_out = stream_duration("v:0"), stream_duration("a:0")
    # 允許不到一格（1/10 秒）的誤差，但不容許秒級的尾巴
    assert video - audio_out < 0.1, f"影像軌比音訊長 {video - audio_out:.3f} 秒"


@pytest.mark.skipif(not HAS_FFMPEG, reason="需要 ffmpeg")
def test_probe_returns_none_without_audio_stream(tmp_path):
    """沒有音訊軌時探測要回 None，不能拋錯或給出容器長度。"""
    from soundstage.render.probe import probe_audio_duration

    image = tmp_path / "still.png"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1", str(image)],
        check=True,
    )

    assert probe_audio_duration(image) is None


@pytest.mark.skipif(not HAS_FFMPEG, reason="需要 ffmpeg")
def test_waveform_render_end_to_end(tmp_path):
    """波形樣式要真的產得出帶影像與音訊的 mp4。

    filter_complex 比靜態封面複雜得多（blend 的色彩空間、showwavespic 只吐
    一格要 loop、播放頭是第三路輸入），純函式測試驗不到這些會不會實際跑通。
    """
    from soundstage.render import VisualStyle

    audio = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(audio)],
        check=True,
    )

    out = render(audio, tmp_path / "wave.mp4", width=320, height=240, fps=10,
                 visual=VisualStyle.WAVEFORM)

    assert out.is_file() and out.stat().st_size > 0
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )
    assert set(probe.stdout.split()) == {"video", "audio"}
