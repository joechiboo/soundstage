"""YouTube OAuth 2.0 授權與 token 快取。

Google 的相依套件是 optional extra（`uv sync --extra upload`），
所以一律在函式內才 import，讓沒裝 extra 的人仍能正常使用 render。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from soundstage.errors import UploadError

# 只要求上傳權限；thumbnails().set 也在這個 scope 涵蓋範圍內。
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

_MISSING_DEPS_HINT = (
    "缺少 YouTube 上傳所需的套件。請先安裝：\n"
    "  uv sync --extra upload"
)

_MISSING_SECRET_HINT = (
    "找不到 OAuth client secret：{path}\n"
    "請到 Google Cloud Console 建立「桌面應用程式」類型的 OAuth 用戶端，\n"
    "下載 JSON 後放到上述路徑（或設環境變數 SOUNDSTAGE_CLIENT_SECRET 指向它）：\n"
    "  1. https://console.cloud.google.com/apis/credentials\n"
    "  2. 啟用 YouTube Data API v3\n"
    "  3. 建立憑證 → OAuth 用戶端 ID → 桌面應用程式"
)


def _import_google() -> tuple[Any, Any, Any]:
    """延遲 import Google 套件，缺套件時給明確訊息。"""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:  # pragma: no cover - 取決於安裝環境
        raise UploadError(_MISSING_DEPS_HINT) from exc
    return Credentials, InstalledAppFlow, Request


def client_secret_path(config_dir: Path) -> Path:
    """client_secret.json 的位置，可用 SOUNDSTAGE_CLIENT_SECRET 覆蓋。"""
    override = os.environ.get("SOUNDSTAGE_CLIENT_SECRET")
    if override:
        return Path(override).expanduser()
    return config_dir / "client_secret.json"


def token_path(config_dir: Path) -> Path:
    """OAuth token 快取的位置。"""
    return config_dir / "token.json"


def save_credentials(credentials: Any, config_dir: Path) -> Path:
    """把 token 寫入快取，權限設為 0600（只有自己讀得到）。"""
    path = token_path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(credentials.to_json(), encoding="utf-8")
    path.chmod(0o600)
    return path


def load_cached_credentials(config_dir: Path) -> Any | None:
    """讀取快取的 token；沒有或格式壞掉都回傳 None。"""
    path = token_path(config_dir)
    if not path.is_file():
        return None

    Credentials, _, _ = _import_google()
    try:
        return Credentials.from_authorized_user_file(str(path), SCOPES)
    except (ValueError, KeyError):
        # 壞掉的快取不該讓整個流程掛掉，重新授權即可
        return None


def _run_flow(
    config_dir: Path,
    *,
    open_browser: bool,
    on_notice: Callable[[str], None] | None = None,
) -> Any:
    """跑完整的 OAuth 授權流程，回傳新的 credentials。"""
    _, InstalledAppFlow, _ = _import_google()

    secret = client_secret_path(config_dir)
    if not secret.is_file():
        raise UploadError(_MISSING_SECRET_HINT.format(path=secret))

    # 確認 client secret 存在後才提示，免得使用者以為瀏覽器要開了卻看到錯誤
    if on_notice is not None:
        on_notice(
            "需要 YouTube 授權，將開啟瀏覽器完成登入…"
            if open_browser
            else "需要 YouTube 授權，請用下方網址在瀏覽器完成登入…"
        )

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
        return flow.run_local_server(port=0, open_browser=open_browser)
    except UploadError:
        raise
    except Exception as exc:
        raise UploadError(f"OAuth 授權流程失敗：{exc}") from exc


def get_credentials(
    config_dir: Path,
    *,
    open_browser: bool = True,
    force_reauth: bool = False,
    on_notice: Callable[[str], None] | None = None,
) -> Any:
    """取得可用的 credentials：優先用快取，過期就 refresh，失效則重新授權。"""
    _, _, Request = _import_google()

    def notify(message: str) -> None:
        if on_notice is not None:
            on_notice(message)

    credentials = None if force_reauth else load_cached_credentials(config_dir)

    if credentials is not None and credentials.valid:
        return credentials

    if credentials is not None and credentials.expired and credentials.refresh_token:
        from google.auth.exceptions import RefreshError

        try:
            credentials.refresh(Request())
        except RefreshError:
            # token 被撤銷或密碼變更等情況，只能重新授權
            notify("已快取的授權失效（可能已被撤銷），重新進行授權…")
            credentials = None
        else:
            save_credentials(credentials, config_dir)
            return credentials

    if credentials is None or not credentials.valid:
        credentials = _run_flow(
            config_dir, open_browser=open_browser, on_notice=on_notice
        )
        save_credentials(credentials, config_dir)

    return credentials


def clear_credentials(config_dir: Path) -> bool:
    """刪除快取的 token，回傳是否真的刪到東西。"""
    path = token_path(config_dir)
    if path.is_file():
        path.unlink()
        return True
    return False
