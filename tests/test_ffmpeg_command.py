from pathlib import Path

from soundstage.render import RenderSpec, VisualStyle, build_render_command


def make_spec(**overrides) -> RenderSpec:
    defaults = dict(
        audio_path=Path("song.wav"),
        cover_path=Path("cover.png"),
        output_path=Path("out.mp4"),
    )
    return RenderSpec(**{**defaults, **overrides})


def test_static_command_structure():
    command = build_render_command(make_spec())

    assert command[0] == "ffmpeg"
    assert command[-1] == "out.mp4"
    assert "-y" in command

    # 圖片輸入要 loop，且圖在音檔之前
    loop_idx = command.index("-loop")
    assert command[loop_idx + 1] == "1"
    inputs = [command[i + 1] for i, arg in enumerate(command) if arg == "-i"]
    assert inputs == ["cover.png", "song.wav"]


def test_static_command_codecs():
    command = build_render_command(make_spec(audio_bitrate="256k"))

    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-c:a") + 1] == "aac"
    assert command[command.index("-b:a") + 1] == "256k"
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert "-shortest" in command


def test_resolution_lands_in_filter():
    command = build_render_command(make_spec(width=1280, height=720))
    vf = command[command.index("-vf") + 1]
    assert "scale=1280:720" in vf
    assert "pad=1280:720" in vf


def test_fps_configurable():
    command = build_render_command(make_spec(fps=2))
    assert command[command.index("-framerate") + 1] == "2"


def test_default_visual_is_static():
    assert make_spec().visual is VisualStyle.STATIC


def test_streams_explicitly_mapped():
    """必須明確指定串流，否則 ffmpeg 會自己挑解析度最高的影像串流。

    音訊來源夾帶影像的情況很常見（手機錄的影片、內嵌專輯封面的 mp3），
    只要它比封面圖大，使用者指定的 --cover 就會被默默忽略。
    """
    command = build_render_command(make_spec())

    assert "-map" in command
    maps = [command[i + 1] for i, arg in enumerate(command) if arg == "-map"]
    assert maps == ["0:v:0", "1:a:0"]

    # -map 必須排在輸入之後、輸出檔之前才有效
    assert command.index("-map") > command.index("-i")
    assert command.index("-map") < len(command) - 1
