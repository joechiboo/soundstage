"""YouTube Data API v3 的請求組裝與呼叫。

build_video_body() 是不碰網路的純函式，方便單元測試與除錯時直接檢視送出的內容，
設計上與 render.build_render_command() 對稱。
"""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Callable

from soundstage.errors import UploadError
from soundstage.meta import Privacy, VideoMeta

# 上傳分塊大小；設定成固定值（而非 -1）才拿得到進度回報。
CHUNK_SIZE = 8 * 1024 * 1024

# 這些 HTTP 狀態碼屬於暫時性錯誤，值得重試。
RETRIABLE_STATUS_CODES = (500, 502, 503, 504)
MAX_RETRIES = 5


def build_video_body(meta: VideoMeta, privacy: Privacy | None = None) -> dict[str, Any]:
    """把 VideoMeta 轉成 videos().insert 的 request body。

    privacy 不為 None 時覆蓋 meta.privacy。
    """
    effective_privacy = privacy if privacy is not None else meta.privacy
    return {
        "snippet": {
            "title": meta.title,
            "description": meta.description,
            "tags": list(meta.tags),
            "categoryId": meta.category_id,
        },
        "status": {
            "privacyStatus": effective_privacy.value,
            "selfDeclaredMadeForKids": False,
        },
    }


def _import_google() -> tuple[Any, Any, Any]:
    """延遲 import Google 套件，缺套件時給明確訊息。"""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:  # pragma: no cover - 取決於安裝環境
        raise UploadError(
            "缺少 YouTube 上傳所需的套件。請先安裝：\n  uv sync --extra upload"
        ) from exc
    return build, HttpError, MediaFileUpload


def describe_http_error(error: Any) -> str:
    """把 googleapiclient 的 HttpError 轉成看得懂的中文訊息。"""
    status = getattr(getattr(error, "resp", None), "status", None)
    detail = getattr(error, "reason", None) or str(error)

    hints = {
        401: "授權已失效或被撤銷，請重新授權：soundstage auth --reset",
        403: (
            "權限不足或配額用盡。常見原因：\n"
            "  - YouTube Data API v3 每日配額用完（上傳一支影片約耗 1600 點，預設每日 10000 點）\n"
            "  - 專案未啟用 YouTube Data API v3\n"
            "  - 帳號尚未建立 YouTube 頻道，或未通過驗證而無法上傳"
        ),
        400: "請求內容不合法，請檢查 metadata 設定檔（標題、標籤、分類 ID）。",
        404: "找不到對應的資源，請確認帳號與頻道設定。",
    }
    message = f"YouTube API 回應錯誤（HTTP {status}）：{detail}"
    if status in hints:
        message += f"\n{hints[status]}"
    return message


def upload_video_file(
    credentials: Any,
    video_path: Path,
    body: dict[str, Any],
    *,
    on_progress: Callable[[float], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """以 resumable upload 上傳影片檔，回傳 YouTube 影片 ID。"""
    build, HttpError, MediaFileUpload = _import_google()

    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    media = MediaFileUpload(str(video_path), chunksize=CHUNK_SIZE, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    attempt = 0
    while response is None:
        try:
            status, response = request.next_chunk()
        except HttpError as exc:
            code = getattr(getattr(exc, "resp", None), "status", None)
            if code in RETRIABLE_STATUS_CODES and attempt < MAX_RETRIES:
                attempt += 1
                sleep(2**attempt)
                continue
            raise UploadError(describe_http_error(exc)) from exc
        except OSError as exc:
            # 網路中斷之類的暫時性問題，resumable upload 可以接著傳
            if attempt < MAX_RETRIES:
                attempt += 1
                sleep(2**attempt)
                continue
            raise UploadError(f"上傳過程中連線失敗：{exc}") from exc
        else:
            attempt = 0
            if status is not None and on_progress is not None:
                on_progress(status.progress())

    video_id = response.get("id")
    if not video_id:
        raise UploadError(f"上傳完成但 YouTube 沒有回傳影片 ID：{response}")

    if on_progress is not None:
        on_progress(1.0)
    return video_id


def set_thumbnail(credentials: Any, video_id: str, thumbnail_path: Path) -> None:
    """替影片設定自訂縮圖。"""
    build, HttpError, MediaFileUpload = _import_google()

    # 副檔名少見時 googleapiclient 猜不出型別會直接拋錯，這裡先給預設值
    mimetype = mimetypes.guess_type(thumbnail_path.name)[0] or "image/jpeg"

    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype=mimetype),
        ).execute()
    except HttpError as exc:
        raise UploadError(describe_http_error(exc)) from exc
