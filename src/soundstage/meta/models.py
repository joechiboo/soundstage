"""meta 模組對外的型別定義。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Privacy(str, Enum):
    """YouTube 影片的公開狀態。"""

    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class VideoMeta(BaseModel):
    """一支影片的 metadata，對應 meta.yaml / meta.json。"""

    model_config = ConfigDict(extra="forbid")

    # 長度上限對齊 YouTube 的限制，先擋在本機比上傳後被 API 退件好除錯
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list)
    privacy: Privacy = Privacy.PRIVATE
    category_id: str = "10"  # YouTube 分類，10 = Music
    thumbnail: Path | None = None

    @field_validator("tags")
    @classmethod
    def _check_tags_total_length(cls, tags: list[str]) -> list[str]:
        # YouTube 限制所有標籤加總不超過 500 字元
        total = sum(len(tag) for tag in tags)
        if total > 500:
            raise ValueError(f"所有標籤長度加總不可超過 500 字元（目前 {total}）")
        return tags
