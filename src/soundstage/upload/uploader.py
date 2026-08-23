"""upload 流程：取得授權 → resumable 上傳影片 → 設定縮圖。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from soundstage.errors import InputFileError, ThumbnailError, UploadError
from soundstage.meta import Privacy, VideoMeta
from soundstage.upload.auth import get_credentials
from soundstage.upload.youtube import (
    build_video_body,
    set_thumbnail,
    upload_video_file,
)

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "soundstage"


def upload_video(
    video_path: Path,
    meta: VideoMeta,
    *,
    privacy: Privacy | None = None,
    config_dir: Path = DEFAULT_CONFIG_DIR,
    open_browser: bool = True,
    on_progress: Callable[[float], None] | None = None,
    on_notice: Callable[[str], None] | None = None,
) -> str:
    """上傳影片到 YouTube，回傳影片 ID。

    privacy 不為 None 時覆蓋 meta.privacy（讓 CLI 可以用 --privacy 臨時切換）。
    影片上傳成功後縮圖才失敗的話，會拋 ThumbnailError（內含 video_id）。
    """
    if not video_path.is_file():
        raise InputFileError(f"找不到影片檔：{video_path}")
    if video_path.stat().st_size == 0:
        raise UploadError(f"影片檔是空的，無法上傳：{video_path}")

    thumbnail = meta.thumbnail
    if thumbnail is not None and not thumbnail.is_file():
        # 在耗時的上傳之前就先擋掉，避免傳完才發現縮圖路徑打錯
        raise InputFileError(f"找不到縮圖檔：{thumbnail}")

    credentials = get_credentials(
        config_dir, open_browser=open_browser, on_notice=on_notice
    )
    body = build_video_body(meta, privacy)

    video_id = upload_video_file(
        credentials, video_path, body, on_progress=on_progress
    )

    if thumbnail is not None:
        try:
            set_thumbnail(credentials, video_id, thumbnail)
        except UploadError as exc:
            raise ThumbnailError(video_id, str(exc)) from exc

    return video_id
