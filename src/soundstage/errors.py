"""soundstage 共用的例外型別。

各模組只拋出這裡定義的例外，CLI 統一攔截後顯示友善訊息。
"""

from __future__ import annotations


class SoundstageError(Exception):
    """所有 soundstage 錯誤的基底類別。"""


class InputFileError(SoundstageError):
    """輸入檔案不存在或無法讀取。"""


class FFmpegNotFoundError(SoundstageError):
    """系統上找不到 ffmpeg 執行檔。"""

    def __init__(self) -> None:
        super().__init__(
            "找不到 ffmpeg。請先安裝：\n"
            "  macOS:  brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: winget install ffmpeg"
        )


class FFmpegError(SoundstageError):
    """ffmpeg 執行失敗。保留退出碼與 stderr 供除錯。"""

    def __init__(self, returncode: int, stderr: str, command: list[str]) -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.command = command
        tail = "\n".join(stderr.strip().splitlines()[-10:])
        super().__init__(
            f"ffmpeg 執行失敗（exit code {returncode}）。\n"
            f"指令：{' '.join(command)}\n"
            f"錯誤輸出：\n{tail}"
        )


class MetaError(SoundstageError):
    """metadata 設定檔格式錯誤或內容不合法。"""


class UploadError(SoundstageError):
    """上傳 YouTube 失敗（含 OAuth 授權問題）。"""
