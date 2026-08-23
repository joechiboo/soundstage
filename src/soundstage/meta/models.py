"""meta 模組對外的型別定義。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Privacy(str, Enum):
    """YouTube 影片的公開狀態。"""

    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class VideoMeta(BaseModel):
    """一支影片的 metadata，對應 meta.yaml / meta.json。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    privacy: Privacy = Privacy.PRIVATE
    category_id: str = "10"  # YouTube 分類，10 = Music
    thumbnail: Path | None = None
