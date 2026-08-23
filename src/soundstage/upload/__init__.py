"""upload 模組：透過 YouTube Data API v3 上傳影片。

其他模組只從這裡 import 公開介面，不要直接 import 內部實作。
"""

from soundstage.upload.auth import (
    clear_credentials,
    client_secret_path,
    get_credentials,
    token_path,
)
from soundstage.upload.uploader import DEFAULT_CONFIG_DIR, upload_video
from soundstage.upload.youtube import build_video_body

__all__ = [
    "DEFAULT_CONFIG_DIR",
    "build_video_body",
    "clear_credentials",
    "client_secret_path",
    "get_credentials",
    "token_path",
    "upload_video",
]
