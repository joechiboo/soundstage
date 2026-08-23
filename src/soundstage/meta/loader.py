"""讀取 yaml / json 的 metadata 設定檔。"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from soundstage.errors import InputFileError, MetaError
from soundstage.meta.models import VideoMeta


def load_meta(path: Path) -> VideoMeta:
    """依副檔名解析設定檔並驗證，回傳 VideoMeta。

    thumbnail 若為相對路徑，會以設定檔所在目錄為基準解析。
    """
    if not path.is_file():
        raise InputFileError(f"找不到 metadata 設定檔：{path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text)
        elif suffix == ".json":
            data = json.loads(text)
        else:
            raise MetaError(f"不支援的設定檔格式：{suffix}（請用 .yaml / .yml / .json）")
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise MetaError(f"設定檔 {path} 解析失敗：{exc}") from exc

    if not isinstance(data, dict):
        raise MetaError(f"設定檔 {path} 內容必須是 key-value 結構")

    try:
        meta = VideoMeta.model_validate(data)
    except ValidationError as exc:
        problems = "\n".join(
            f"  - {'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        raise MetaError(f"設定檔 {path} 內容不合法：\n{problems}") from exc

    if meta.thumbnail is not None and not meta.thumbnail.is_absolute():
        meta.thumbnail = (path.parent / meta.thumbnail).resolve()
    return meta
