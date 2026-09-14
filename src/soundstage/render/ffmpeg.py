"""ffmpeg 指令組裝。

這裡只負責把 RenderSpec 轉成 argv list，不執行任何 subprocess，
讓指令內容可以被單元測試直接驗證，除錯時也能原樣印出來手動重跑。
"""

from __future__ import annotations

from typing import Callable

from soundstage.render.spec import RenderSpec, VisualStyle


# -t 要比音訊長度多一點點，不能剛好等於：音訊編碼器只能輸出完整的 frame，
# 切在正好的長度上會少掉最後一格（實測 16kHz 的 AAC 少 64ms，就是 1024
# samples 的長度）。0.25 秒足以覆蓋常見編碼的單格長度（AAC 1024 samples
# 在 8kHz 是 128ms，MP3 1152 samples 在 8kHz 是 144ms），而多出來的部分
# 由 -shortest 收掉——實測輸出的影像軌反而比音訊短 8～19ms，不到一格。
_DURATION_EPSILON = 0.25


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
    command = [
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
    ]
    # -loop 1 的封面是無限長的影像串流，單靠 -shortest 收不乾淨：實測影像軌
    # 會比音訊多出 2 秒左右（兩支素材分別是 2.06s 與 2.28s），尾巴多一段無聲
    # 畫面，而 ffmpeg 不會有任何警告。用探測到的音訊長度硬切才準（誤差 14ms，
    # 不到 30fps 的半格）。-shortest_buf_duration 試過無效，-fflags +shortest
    # 在新版 ffmpeg 已移除。
    if spec.duration is not None:
        command += ["-t", f"{spec.duration + _DURATION_EPSILON:.6f}"]
    # -shortest 保留：探測不到長度時它是唯一的收尾機制，探測得到時也能擋住
    # 音訊比宣稱長度更早結束的情況。
    command += [
        "-shortest",
        "-movflags", "+faststart",
        str(spec.output_path),
    ]
    return command


_WAVEFORM_COLOR = "0x7FC8FF"
_PLAYHEAD_WIDTH = 5


def _even(value: int) -> int:
    """H.264 的 yuv420p 對尺寸與位移都比較安全的做法是一律取偶數。"""
    return value - (value % 2)


def _waveform_layout(spec: RenderSpec) -> tuple[int, int, int, int]:
    """波形在畫面上的位置：置中、放在下三分之一，把中央留給封面的標題。"""
    wave_w = _even(int(spec.width * 0.83))
    wave_h = _even(int(spec.height * 0.28))
    return wave_w, wave_h, _even((spec.width - wave_w) // 2), _even(int(spec.height * 0.61))


def _build_waveform_command(spec: RenderSpec) -> list[str]:
    """波形視覺化：封面當背景，疊上整首的波形圖與隨音樂移動的播放頭。

    刻意用 showwavespic（整首一張靜態波形）而不是 showwaves（示波器）：
    showwaves 每一格只畫 1/fps 秒的音訊，取樣率低的素材連畫面寬度都填不滿
    （16kHz 在 30fps 下只有 533 個取樣要鋪滿 1920 像素，其餘留白），而且
    每格只看得到 33 毫秒，讀不出樂曲的強弱結構。整首波形配上播放頭反而
    看得出分句。
    """
    w, h = spec.width, spec.height
    wave_w, wave_h, wave_x, wave_y = _waveform_layout(spec)

    chains = [
        # blend 必須在 RGB 平面上做。走預設的 YUV 的話，screen 會被套到色度
        # 平面上，輸出會整片變成洋紅色。
        f"[0:v]{_scale_pad_filter(spec)},setsar=1,format=gbrp[bg]",
        f"[1:a]showwavespic=s={wave_w}x{wave_h}:colors={_WAVEFORM_COLOR}[pic]",
        # showwavespic 只吐一格，loop 成連續串流才能跟背景逐格混合
        f"[pic]pad={w}:{h}:{wave_x}:{wave_y}:color=black,"
        f"loop=loop=-1:size=1:start=0,setpts=N/{spec.fps}/TB,format=gbrp[wave]",
        # 波形圖的底是黑的，screen 混合時黑色不改變背景，等於免費去背
        "[bg][wave]blend=all_mode=screen:shortest=1[base]",
    ]

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-loop", "1",
        "-framerate", str(spec.fps),
        "-i", str(spec.cover_path),
        "-i", str(spec.audio_path),
    ]

    if spec.duration is not None:
        # 播放頭用 overlay 而不是 drawbox：drawbox 的運算式裡 t 是「線寬」，
        # 沒有時間變數（n 也沒定義），拿 t 當時間會算出畫面外的座標，
        # 而且 ffmpeg 不會報錯——box 就這樣無聲無息地消失。
        command += ["-f", "lavfi", "-i", f"color=c=white:s={_PLAYHEAD_WIDTH}x{wave_h}"]
        chains.append("[2:v]format=gbrp[ph]")
        chains.append(
            f"[base][ph]overlay=x='{wave_x}+{wave_w}*t/{spec.duration:.6f}':"
            f"y={wave_y}:shortest=1,format=yuv420p[v]"
        )
    else:
        # 探測不到長度就畫不出播放頭的位置，只保留波形
        chains.append("[base]format=yuv420p[v]")

    command += [
        "-filter_complex", ";".join(chains),
        "-map", "[v]",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", spec.audio_bitrate,
    ]
    if spec.duration is not None:
        command += ["-t", f"{spec.duration + _DURATION_EPSILON:.6f}"]
    command += [
        "-shortest",
        "-movflags", "+faststart",
        str(spec.output_path),
    ]
    return command


# 視覺化樣式 → 指令組裝函式。之後的 spectrum 在這裡註冊即可。
_COMMAND_BUILDERS: dict[VisualStyle, Callable[[RenderSpec], list[str]]] = {
    VisualStyle.STATIC: _build_static_command,
    VisualStyle.WAVEFORM: _build_waveform_command,
}


def build_render_command(spec: RenderSpec) -> list[str]:
    """把 RenderSpec 轉成 ffmpeg argv list。"""
    try:
        builder = _COMMAND_BUILDERS[spec.visual]
    except KeyError:  # pragma: no cover - enum 新增樣式但忘了註冊時的保險
        raise NotImplementedError(f"尚未支援的視覺化樣式：{spec.visual}") from None
    return builder(spec)
