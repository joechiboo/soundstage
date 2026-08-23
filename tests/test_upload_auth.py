"""OAuth token 快取與重新授權流程。"""

import json

import pytest

from soundstage.errors import UploadError
from soundstage.upload import auth

pytest.importorskip("google.oauth2", reason="需要 uv sync --extra upload")


class FakeCredentials:
    def __init__(self, *, valid=True, expired=False, refresh_token="rt"):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refreshed = False

    def to_json(self):
        return json.dumps({"token": "fake"})

    def refresh(self, request):
        self.refreshed = True
        self.valid = True
        self.expired = False


def test_client_secret_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDSTAGE_CLIENT_SECRET", str(tmp_path / "custom.json"))
    assert auth.client_secret_path(tmp_path) == tmp_path / "custom.json"


def test_client_secret_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SOUNDSTAGE_CLIENT_SECRET", raising=False)
    assert auth.client_secret_path(tmp_path) == tmp_path / "client_secret.json"


def test_save_credentials_is_private(tmp_path):
    path = auth.save_credentials(FakeCredentials(), tmp_path)
    assert path.is_file()
    assert path.stat().st_mode & 0o077 == 0  # 其他人不可讀


def test_valid_cache_is_reused(tmp_path, monkeypatch):
    cached = FakeCredentials(valid=True)
    monkeypatch.setattr(auth, "load_cached_credentials", lambda _: cached)
    monkeypatch.setattr(
        auth, "_run_flow", lambda *a, **k: pytest.fail("不該重新授權")
    )

    assert auth.get_credentials(tmp_path) is cached


def test_expired_cache_is_refreshed(tmp_path, monkeypatch):
    cached = FakeCredentials(valid=False, expired=True)
    monkeypatch.setattr(auth, "load_cached_credentials", lambda _: cached)
    monkeypatch.setattr(
        auth, "_run_flow", lambda *a, **k: pytest.fail("refresh 成功就不該重新授權")
    )

    result = auth.get_credentials(tmp_path)

    assert result is cached and cached.refreshed
    assert auth.token_path(tmp_path).is_file()  # refresh 後要回寫快取


def test_revoked_token_triggers_reauth(tmp_path, monkeypatch):
    from google.auth.exceptions import RefreshError

    class Revoked(FakeCredentials):
        def refresh(self, request):
            raise RefreshError("revoked")

    fresh = FakeCredentials(valid=True)
    monkeypatch.setattr(
        auth, "load_cached_credentials", lambda _: Revoked(valid=False, expired=True)
    )
    monkeypatch.setattr(auth, "_run_flow", lambda *a, **k: fresh)

    notices = []
    result = auth.get_credentials(tmp_path, on_notice=notices.append)

    assert result is fresh
    assert any("失效" in n for n in notices)


def test_force_reauth_ignores_cache(tmp_path, monkeypatch):
    fresh = FakeCredentials()
    monkeypatch.setattr(
        auth, "load_cached_credentials", lambda _: pytest.fail("不該讀快取")
    )
    monkeypatch.setattr(auth, "_run_flow", lambda *a, **k: fresh)

    assert auth.get_credentials(tmp_path, force_reauth=True) is fresh


def test_missing_client_secret_message(tmp_path, monkeypatch):
    monkeypatch.delenv("SOUNDSTAGE_CLIENT_SECRET", raising=False)
    with pytest.raises(UploadError, match="client secret"):
        auth._run_flow(tmp_path, open_browser=False)


def test_corrupt_cache_returns_none(tmp_path):
    auth.token_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    auth.token_path(tmp_path).write_text("not json", encoding="utf-8")
    assert auth.load_cached_credentials(tmp_path) is None


def test_clear_credentials(tmp_path):
    auth.save_credentials(FakeCredentials(), tmp_path)
    assert auth.clear_credentials(tmp_path) is True
    assert auth.clear_credentials(tmp_path) is False  # 已經沒東西可刪
