"""upload 模組：透過 YouTube Data API v3 上傳影片。

其他模組只從這裡 import 公開介面，不要直接 import 內部實作。
"""

from soundstage.upload.uploader import upload_video

__all__ = ["upload_video"]
