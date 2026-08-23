"""render 模組對外的型別定義。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class VisualStyle(str, Enum):
    """影片視覺化樣式。

    目前只有靜態封面；波形／頻譜是預留的擴充點，
    新增樣式時在 ffmpeg.py 的 _COMMAND_BUILDERS 註冊對應的指令組裝函式。
    """

    STATIC = "static"
    # TODO: WAVEFORM = "waveform"   # ffmpeg showwaves filter
    # TODO: SPECTRUM = "spectrum"   # ffmpeg showspectrum filter


class RenderSpec(BaseModel):
    """一次 render 所需的全部參數。

    build_render_command() 只吃這個型別，不碰檔案系統，
    方便單元測試與除錯時直接印出指令。
    """

    audio_path: Path
    cover_path: Path
    output_path: Path
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    fps: int = Field(default=30, gt=0)
    audio_bitrate: str = "192k"
    visual: VisualStyle = VisualStyle.STATIC
