"""預設封面產生：純色背景 + 檔名文字。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# CJK 字型優先（也能顯示英文），找不到再退回西文字型
_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def make_fallback_cover(
    title: str,
    output_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    bg_color: str = "#1e2a38",
    text_color: str = "#f5f0e8",
) -> Path:
    """產生純色背景加置中文字的封面圖，回傳圖片路徑。"""
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    font_size = max(24, width // 20)
    font = _load_font(font_size)

    # 文字太寬就逐步縮小字級，最低 24px
    while font_size > 24:
        left, top, right, bottom = draw.textbbox((0, 0), title, font=font)
        if right - left <= width * 0.9:
            break
        font_size = int(font_size * 0.9)
        font = _load_font(font_size)

    left, top, right, bottom = draw.textbbox((0, 0), title, font=font)
    x = (width - (right - left)) / 2 - left
    y = (height - (bottom - top)) / 2 - top
    draw.text((x, y), title, font=font, fill=text_color)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
