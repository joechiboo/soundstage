"""ffmpeg 指令組裝。

這裡只負責把 RenderSpec 轉成 argv list，不執行任何 subprocess，
讓指令內容可以被單元測試直接驗證，除錯時也能原樣印出來手動重跑。
"""

from __future__ import annotations

from typing import Callable

from soundstage.render.spec import RenderSpec, VisualStyle


def _scale_pad_filter(spec: RenderSpec) -> str:
    """把封面圖等比縮放進目標解析度，不足處補黑邊，並保證偶數尺寸。"""
    w, h = spec.width, spec.height
    # force_divisible_by=2 確保縮放後的中間尺寸也是偶數，否則四捨五入
    # 可能算出比 pad 目標還大的尺寸，pad 會直接報錯。
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"
    )


def _build_static_command(spec: RenderSpec) -> list[str]:
    """靜態封面：單張圖 loop 成影像軌，配上音軌。"""
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-loop", "1",
        "-framerate", str(spec.fps),
        "-i", str(spec.cover_path),
        "-i", str(spec.audio_path),
        # 明確指定串流來源，不能依賴 ffmpeg 的預設挑選：預設會挑「解析度最高」
        # 的影像串流，所以當音訊來源本身帶有影像時（影片檔、內嵌專輯封面的 mp3），
        # 只要它比封面圖大，封面就會被無聲無息地換掉。
        "-map", "0:v:0",  # 影像固定取自封面圖
        "-map", "1:a:0",  # 音訊固定取自音檔，順帶忽略它可能夾帶的影像
        "-vf", _scale_pad_filter(spec),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", spec.audio_bitrate,
        "-shortest",
        "-movflags", "+faststart",
        str(spec.output_path),
    ]


# 視覺化樣式 → 指令組裝函式。之後的 waveform / spectrum 在這裡註冊即可。
_COMMAND_BUILDERS: dict[VisualStyle, Callable[[RenderSpec], list[str]]] = {
    VisualStyle.STATIC: _build_static_command,
}


def build_render_command(spec: RenderSpec) -> list[str]:
    """把 RenderSpec 轉成 ffmpeg argv list。"""
    try:
        builder = _COMMAND_BUILDERS[spec.visual]
    except KeyError:  # pragma: no cover - enum 新增樣式但忘了註冊時的保險
        raise NotImplementedError(f"尚未支援的視覺化樣式：{spec.visual}") from None
    return builder(spec)
