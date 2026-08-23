"""YouTube 上傳（stub，下一輪實作）。

TODO（實作清單）：
  1. OAuth 2.0 授權流程：
     - 讀取 client_secret.json（路徑：~/.config/soundstage/client_secret.json，
       可用環境變數 SOUNDSTAGE_CLIENT_SECRET 覆蓋）
     - google-auth-oauthlib 的 InstalledAppFlow 跑 local server flow
     - token 快取到 ~/.config/soundstage/token.json，過期自動 refresh，
       refresh 失敗時拋 UploadError 並提示重新授權
  2. 上傳影片：
     - google-api-python-client 的 videos().insert，用 resumable upload
     - snippet（title / description / tags / categoryId）與
       status（privacyStatus）都從 VideoMeta 帶入
  3. 縮圖：meta.thumbnail 有設定時呼叫 thumbnails().set
  4. 相依套件：uv sync --extra upload
"""

from __future__ import annotations

from pathlib import Path

from soundstage.errors import InputFileError, UploadError
from soundstage.meta import Privacy, VideoMeta

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "soundstage"


def upload_video(
    video_path: Path,
    meta: VideoMeta,
    *,
    privacy: Privacy | None = None,
    config_dir: Path = DEFAULT_CONFIG_DIR,
) -> str:
    """上傳影片到 YouTube，回傳影片 ID。

    privacy 不為 None 時覆蓋 meta.privacy（讓 CLI 可以用 --privacy 臨時切換）。
    """
    if not video_path.is_file():
        raise InputFileError(f"找不到影片檔：{video_path}")

    raise UploadError(
        "upload 功能尚未實作（規劃於下一輪）。\n"
        "影片已可先用 render 產出，之後再手動上傳或等 upload 完成。"
    )
