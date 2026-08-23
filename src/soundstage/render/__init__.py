"""render 模組：音檔 + 封面圖 → mp4。

其他模組只從這裡 import 公開介面，不要直接 import 內部實作。
"""

from soundstage.render.ffmpeg import build_render_command
from soundstage.render.renderer import render
from soundstage.render.spec import RenderSpec, VisualStyle

__all__ = ["RenderSpec", "VisualStyle", "build_render_command", "render"]
