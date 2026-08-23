"""meta 模組：影片 metadata 的型別與設定檔載入。

其他模組只從這裡 import 公開介面，不要直接 import 內部實作。
"""

from soundstage.meta.loader import load_meta
from soundstage.meta.models import Privacy, VideoMeta

__all__ = ["Privacy", "VideoMeta", "load_meta"]
