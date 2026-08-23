"""soundstage CLI 進入點。

CLI 只負責參數解析與錯誤呈現，實際邏輯都在 render / meta / upload 模組。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from soundstage.errors import SoundstageError
from soundstage.meta import Privacy, load_meta
from soundstage.render import render as render_video
from soundstage.upload import upload_video

app = typer.Typer(
    name="soundstage",
    help="把音檔（鋼琴或任何錄音）合成影片，並上傳到 YouTube。",
    no_args_is_help=True,
)


def _fail(exc: SoundstageError) -> typer.Exit:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    return typer.Exit(code=1)


def _print_command(command: list[str]) -> None:
    typer.secho("$ " + " ".join(command), fg=typer.colors.BRIGHT_BLACK)


def _do_render(
    audio: Path,
    cover: Path | None,
    output: Path | None,
    width: int,
    height: int,
    fps: int,
    verbose: bool,
) -> Path:
    out = output if output is not None else audio.with_suffix(".mp4")
    result = render_video(
        audio_path=audio,
        output_path=out,
        cover_path=cover,
        width=width,
        height=height,
        fps=fps,
        on_command=_print_command if verbose else None,
    )
    typer.secho(f"已輸出影片：{result}", fg=typer.colors.GREEN)
    return result


CoverOpt = Annotated[Optional[Path], typer.Option("--cover", help="封面圖路徑（不給則用純色背景 + 檔名）")]
WidthOpt = Annotated[int, typer.Option("--width", help="影片寬度")]
HeightOpt = Annotated[int, typer.Option("--height", help="影片高度")]
FpsOpt = Annotated[int, typer.Option("--fps", help="影片 fps")]
VerboseOpt = Annotated[bool, typer.Option("--verbose", "-v", help="顯示實際執行的 ffmpeg 指令")]
MetaOpt = Annotated[Path, typer.Option("--meta", help="metadata 設定檔（yaml / json）")]
PrivacyOpt = Annotated[
    Optional[Privacy],
    typer.Option("--privacy", help="覆蓋設定檔中的公開狀態（private / unlisted / public）"),
]


@app.command()
def render(
    audio: Annotated[Path, typer.Argument(help="輸入音檔（wav / mp3 / flac ...）")],
    cover: CoverOpt = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="輸出 mp4 路徑（預設與音檔同名）")] = None,
    width: WidthOpt = 1920,
    height: HeightOpt = 1080,
    fps: FpsOpt = 30,
    verbose: VerboseOpt = False,
) -> None:
    """把音檔 + 封面圖合成 mp4。"""
    try:
        _do_render(audio, cover, output, width, height, fps, verbose)
    except SoundstageError as exc:
        raise _fail(exc) from exc


@app.command()
def upload(
    video: Annotated[Path, typer.Argument(help="要上傳的影片檔")],
    meta: MetaOpt,
    privacy: PrivacyOpt = None,
) -> None:
    """把影片上傳到 YouTube（尚未實作，下一輪完成）。"""
    try:
        video_meta = load_meta(meta)
        video_id = upload_video(video, video_meta, privacy=privacy)
        typer.secho(f"上傳完成：https://youtu.be/{video_id}", fg=typer.colors.GREEN)
    except SoundstageError as exc:
        raise _fail(exc) from exc


@app.command()
def publish(
    audio: Annotated[Path, typer.Argument(help="輸入音檔（wav / mp3 / flac ...）")],
    meta: MetaOpt,
    cover: CoverOpt = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="中間產物 mp4 路徑（預設與音檔同名）")] = None,
    privacy: PrivacyOpt = None,
    width: WidthOpt = 1920,
    height: HeightOpt = 1080,
    fps: FpsOpt = 30,
    verbose: VerboseOpt = False,
) -> None:
    """render + upload 一次做完。"""
    try:
        video_meta = load_meta(meta)  # 先驗證 metadata，避免 render 完才發現設定檔壞掉
        video_path = _do_render(audio, cover, output, width, height, fps, verbose)
        video_id = upload_video(video_path, video_meta, privacy=privacy)
        typer.secho(f"上傳完成：https://youtu.be/{video_id}", fg=typer.colors.GREEN)
    except SoundstageError as exc:
        raise _fail(exc) from exc


if __name__ == "__main__":
    app()
