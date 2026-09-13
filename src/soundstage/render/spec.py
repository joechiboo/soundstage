"""render 模組對外的型別定義。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


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
    # 音訊長度（秒），由 probe.probe_audio_duration() 探測後填入。
    # None 代表探測不到，指令組裝時會退回只用 -shortest 收尾。
    duration: float | None = Field(default=None, gt=0)

    @field_validator("width", "height")
    @classmethod
    def _must_be_even(cls, value: int) -> int:
        # H.264 的 yuv420p 色度取樣要求長寬都是偶數，奇數會讓 ffmpeg
        # 丟出跟尺寸無關的難懂錯誤，不如在這裡講清楚。
        if value % 2 != 0:
            raise ValueError(f"必須是偶數（H.264 限制），收到 {value}")
        return value
