"""render 流程：驗證輸入 → 準備封面 → 執行 ffmpeg。"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from soundstage.errors import (
    FFmpegError,
    FFmpegNotFoundError,
    InputFileError,
    RenderConfigError,
)
from soundstage.render.cover import make_fallback_cover, validate_cover_image
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
    if cover_path is not None:
        if not cover_path.is_file():
            raise InputFileError(f"找不到封面圖：{cover_path}")
        validate_cover_image(cover_path)
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError()

    with tempfile.TemporaryDirectory(prefix="soundstage-") as tmpdir:
        # 先決定封面路徑並建好 spec，讓參數錯誤在做任何實際工作之前就浮現
        fallback_cover = Path(tmpdir) / "cover.png"
        try:
            spec = RenderSpec(
                audio_path=audio_path,
                cover_path=cover_path if cover_path is not None else fallback_cover,
                output_path=output_path,
                width=width,
                height=height,
                fps=fps,
                visual=visual,
            )
        except ValidationError as exc:
            problems = "\n".join(
                f"  - {'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            raise RenderConfigError(f"render 參數不合法：\n{problems}") from exc

        if cover_path is None:
            make_fallback_cover(
                title=audio_path.stem,
                output_path=fallback_cover,
                width=spec.width,
                height=spec.height,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = build_render_command(spec)
        if on_command is not None:
            on_command(command)

        # stdin 導向 /dev/null：ffmpeg 會把 stdin 當互動指令來源，
        # 在背景執行或被管線包住時可能因此停住不動。
        result = subprocess.run(
            command, capture_output=True, text=True, stdin=subprocess.DEVNULL
        )
        if result.returncode != 0:
            raise FFmpegError(result.returncode, result.stderr, command)

    return output_path
