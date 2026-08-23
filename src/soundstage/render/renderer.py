"""render 流程：驗證輸入 → 準備封面 → 執行 ffmpeg。"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from soundstage.errors import FFmpegError, FFmpegNotFoundError, InputFileError
from soundstage.render.cover import make_fallback_cover
from soundstage.render.ffmpeg import build_render_command
from soundstage.render.spec import RenderSpec, VisualStyle


def render(
    audio_path: Path,
    output_path: Path,
    *,
    cover_path: Path | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    visual: VisualStyle = VisualStyle.STATIC,
    on_command: Callable[[list[str]], None] | None = None,
) -> Path:
    """把音檔合成 mp4，回傳輸出檔路徑。

    cover_path 為 None 時自動產生「純色背景 + 檔名」的封面。
    on_command 收到即將執行的 ffmpeg argv list（供 --verbose 顯示）。
    """
    if not audio_path.is_file():
        raise InputFileError(f"找不到音檔：{audio_path}")
    if cover_path is not None and not cover_path.is_file():
        raise InputFileError(f"找不到封面圖：{cover_path}")
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="soundstage-") as tmpdir:
        if cover_path is None:
            cover_path = make_fallback_cover(
                title=audio_path.stem,
                output_path=Path(tmpdir) / "cover.png",
                width=width,
                height=height,
            )

        spec = RenderSpec(
            audio_path=audio_path,
            cover_path=cover_path,
            output_path=output_path,
            width=width,
            height=height,
            fps=fps,
            visual=visual,
        )
        command = build_render_command(spec)
        if on_command is not None:
            on_command(command)

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(result.returncode, result.stderr, command)

    return output_path
