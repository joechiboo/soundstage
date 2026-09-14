"""soundstage CLI 進入點。

CLI 只負責參數解析與錯誤呈現，實際邏輯都在 render / meta / upload 模組。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from soundstage.errors import SoundstageError
from soundstage.meta import Privacy, VideoMeta, load_meta
from soundstage.render import VisualStyle
from soundstage.render import render as render_video
from soundstage.upload import (
    DEFAULT_CONFIG_DIR,
    clear_credentials,
    client_secret_path,
    get_credentials,
    token_path,
    upload_video,
)

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


def _notice(message: str) -> None:
    typer.secho(message, fg=typer.colors.YELLOW)


def _show_progress(fraction: float) -> None:
    """在同一行更新上傳進度。"""
    percent = int(fraction * 100)
    end = "\n" if percent >= 100 else ""
    print(f"\r上傳中… {percent:3d}%", end=end, flush=True)


def _do_render(
    audio: Path,
    cover: Path | None,
    output: Path | None,
    width: int,
    height: int,
    fps: int,
    verbose: bool,
    visual: VisualStyle = VisualStyle.STATIC,
) -> Path:
    out = output if output is not None else audio.with_suffix(".mp4")
    result = render_video(
        audio_path=audio,
        output_path=out,
        cover_path=cover,
        width=width,
        height=height,
        fps=fps,
        visual=visual,
        on_command=_print_command if verbose else None,
    )
    typer.secho(f"已輸出影片：{result}", fg=typer.colors.GREEN)
    return result


def _do_upload(
    video: Path,
    meta: VideoMeta,
    privacy: Privacy | None,
    config_dir: Path,
    open_browser: bool,
) -> None:
    video_id = upload_video(
        video,
        meta,
        privacy=privacy,
        config_dir=config_dir,
        open_browser=open_browser,
        on_progress=_show_progress if sys.stdout.isatty() else None,
        on_notice=_notice,
    )
    effective = privacy if privacy is not None else meta.privacy
    typer.secho(
        f"上傳完成（{effective.value}）：https://youtu.be/{video_id}",
        fg=typer.colors.GREEN,
    )


CoverOpt = Annotated[Optional[Path], typer.Option("--cover", help="封面圖路徑（不給則用純色背景 + 檔名）")]
WidthOpt = Annotated[int, typer.Option("--width", help="影片寬度")]
HeightOpt = Annotated[int, typer.Option("--height", help="影片高度")]
FpsOpt = Annotated[int, typer.Option("--fps", help="影片 fps")]
VerboseOpt = Annotated[bool, typer.Option("--verbose", "-v", help="顯示實際執行的 ffmpeg 指令")]
VisualOpt = Annotated[VisualStyle, typer.Option("--visual", help="視覺化樣式：static 靜態封面 / waveform 波形")]
MetaOpt = Annotated[Path, typer.Option("--meta", help="metadata 設定檔（yaml / json）")]
PrivacyOpt = Annotated[
    Optional[Privacy],
    typer.Option("--privacy", help="覆蓋設定檔中的公開狀態（private / unlisted / public）"),
]
ConfigDirOpt = Annotated[
    Path, typer.Option("--config-dir", help="OAuth 憑證與 token 的存放目錄")
]
NoBrowserOpt = Annotated[
    bool,
    typer.Option("--no-browser", help="不自動開瀏覽器，改在終端機顯示授權網址（適合遠端主機）"),
]


@app.command()
def render(
    audio: Annotated[Path, typer.Argument(help="輸入音檔（wav / mp3 / flac ...）")],
    cover: CoverOpt = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="輸出 mp4 路徑（預設與音檔同名）")] = None,
    width: WidthOpt = 1920,
    height: HeightOpt = 1080,
    fps: FpsOpt = 30,
    visual: VisualOpt = VisualStyle.STATIC,
    verbose: VerboseOpt = False,
) -> None:
    """把音檔 + 封面圖合成 mp4。"""
    try:
        _do_render(audio, cover, output, width, height, fps, verbose, visual)
    except SoundstageError as exc:
        raise _fail(exc) from exc


@app.command()
def upload(
    video: Annotated[Path, typer.Argument(help="要上傳的影片檔")],
    meta: MetaOpt,
    privacy: PrivacyOpt = None,
    config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR,
    no_browser: NoBrowserOpt = False,
) -> None:
    """把影片上傳到 YouTube。"""
    try:
        video_meta = load_meta(meta)
        _do_upload(video, video_meta, privacy, config_dir, not no_browser)
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
    visual: VisualOpt = VisualStyle.STATIC,
    verbose: VerboseOpt = False,
    config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR,
    no_browser: NoBrowserOpt = False,
) -> None:
    """render + upload 一次做完。"""
    try:
        video_meta = load_meta(meta)  # 先驗證 metadata，避免 render 完才發現設定檔壞掉
        video_path = _do_render(audio, cover, output, width, height, fps, verbose, visual)
        _do_upload(video_path, video_meta, privacy, config_dir, not no_browser)
    except SoundstageError as exc:
        raise _fail(exc) from exc


@app.command()
def auth(
    reset: Annotated[bool, typer.Option("--reset", help="刪除已快取的 token，下次重新授權")] = False,
    status: Annotated[bool, typer.Option("--status", help="只顯示目前的憑證狀態，不進行授權")] = False,
    config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR,
    no_browser: NoBrowserOpt = False,
) -> None:
    """管理 YouTube 授權（預先授權、查看狀態、清除 token）。"""
    try:
        if reset:
            removed = clear_credentials(config_dir)
            message = (
                f"已刪除 token：{token_path(config_dir)}"
                if removed
                else "沒有可刪除的 token 快取。"
            )
            typer.secho(message, fg=typer.colors.GREEN)
            return

        if status:
            secret = client_secret_path(config_dir)
            token = token_path(config_dir)
            typer.echo(f"client secret：{secret}（{'存在' if secret.is_file() else '不存在'}）")
            typer.echo(f"token 快取：  {token}（{'存在' if token.is_file() else '不存在'}）")
            return

        get_credentials(config_dir, open_browser=not no_browser, on_notice=_notice)
        typer.secho(
            f"授權完成，token 已存到 {token_path(config_dir)}", fg=typer.colors.GREEN
        )
    except SoundstageError as exc:
        raise _fail(exc) from exc


if __name__ == "__main__":
    app()
