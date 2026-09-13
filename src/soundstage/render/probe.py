"""用 ffprobe 探測輸入檔資訊。

跟 ffmpeg.py 的純函式設計相反，這裡必須真的跑 subprocess，
所以獨立成一個模組，讓「組指令」與「探測輸入」兩件事分開。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _parse_duration(raw: object) -> float | None:
    """ffprobe 取不到的欄位會給 "N/A" 或空字串，不是缺鍵。"""
    text = str(raw).strip()
    if not text or text == "N/A":
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


def probe_audio_duration(path: Path) -> float | None:
    """回傳第一條音訊軌的長度（秒），探測不到時回傳 None。

    優先用音訊軌自己的 duration，容器的 format duration 只當備援：影片檔的
    容器長度是以較長的那條串流為準，拿來當音訊長度會多算（實測一支手機錄影
    的容器是 147.783s，音訊軌其實只有 147.752s）。
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=duration:format=duration",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
    except OSError:
        # ffprobe 不存在或無法執行。探測失敗不該讓整個 render 掛掉，
        # 呼叫端會退回 -shortest。
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    for stream in data.get("streams", []):
        duration = _parse_duration(stream.get("duration", ""))
        if duration is not None:
            return duration
    return _parse_duration(data.get("format", {}).get("duration", ""))
