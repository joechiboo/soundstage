"""upload 流程測試：用假的 credentials 與假的 API 呼叫，不碰網路。"""

import pytest

from soundstage.errors import InputFileError, ThumbnailError, UploadError
from soundstage.meta import Privacy, VideoMeta
from soundstage.upload import uploader


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "out.mp4"
    path.write_bytes(b"fake video bytes")
    return path


@pytest.fixture
def patched(monkeypatch):
    """把 auth 與 YouTube 呼叫換成假的，記錄收到的參數。"""
    calls = {"uploads": [], "thumbnails": [], "credentials": []}

    def fake_get_credentials(config_dir, **kwargs):
        calls["credentials"].append((config_dir, kwargs))
        return "fake-credentials"

    def fake_upload(credentials, video_path, body, **kwargs):
        calls["uploads"].append({"body": body, "path": video_path})
        if kwargs.get("on_progress"):
            kwargs["on_progress"](0.5)
        return "video-123"

    def fake_set_thumbnail(credentials, video_id, thumbnail_path):
        calls["thumbnails"].append((video_id, thumbnail_path))

    monkeypatch.setattr(uploader, "get_credentials", fake_get_credentials)
    monkeypatch.setattr(uploader, "upload_video_file", fake_upload)
    monkeypatch.setattr(uploader, "set_thumbnail", fake_set_thumbnail)
    return calls


def test_upload_returns_video_id(video, patched, tmp_path):
    meta = VideoMeta(title="demo")
    video_id = uploader.upload_video(video, meta, config_dir=tmp_path)

    assert video_id == "video-123"
    assert patched["uploads"][0]["body"]["snippet"]["title"] == "demo"
    assert patched["thumbnails"] == []  # 沒設 thumbnail 就不該呼叫


def test_privacy_override_reaches_api(video, patched, tmp_path):
    meta = VideoMeta(title="demo", privacy=Privacy.PRIVATE)
    uploader.upload_video(video, meta, privacy=Privacy.PUBLIC, config_dir=tmp_path)

    body = patched["uploads"][0]["body"]
    assert body["status"]["privacyStatus"] == "public"


def test_progress_callback_forwarded(video, patched, tmp_path):
    seen = []
    uploader.upload_video(
        video, VideoMeta(title="demo"), config_dir=tmp_path, on_progress=seen.append
    )
    assert seen == [0.5]


def test_thumbnail_uploaded_when_present(video, patched, tmp_path):
    thumb = tmp_path / "thumb.jpg"
    thumb.write_bytes(b"fake jpg")
    meta = VideoMeta(title="demo", thumbnail=thumb)

    uploader.upload_video(video, meta, config_dir=tmp_path)

    assert patched["thumbnails"] == [("video-123", thumb)]


def test_missing_video(tmp_path, patched):
    with pytest.raises(InputFileError, match="找不到影片檔"):
        uploader.upload_video(tmp_path / "nope.mp4", VideoMeta(title="demo"))


def test_empty_video_rejected(tmp_path, patched):
    empty = tmp_path / "empty.mp4"
    empty.touch()
    with pytest.raises(UploadError, match="空的"):
        uploader.upload_video(empty, VideoMeta(title="demo"))


def test_missing_thumbnail_checked_before_upload(video, patched, tmp_path):
    meta = VideoMeta(title="demo", thumbnail=tmp_path / "nope.jpg")

    with pytest.raises(InputFileError, match="找不到縮圖檔"):
        uploader.upload_video(video, meta, config_dir=tmp_path)

    # 重點：還沒開始上傳就該擋下來
    assert patched["uploads"] == []


def test_thumbnail_failure_keeps_video_id(video, patched, tmp_path, monkeypatch):
    thumb = tmp_path / "thumb.jpg"
    thumb.write_bytes(b"fake jpg")

    def boom(credentials, video_id, thumbnail_path):
        raise UploadError("HTTP 403")

    monkeypatch.setattr(uploader, "set_thumbnail", boom)
    meta = VideoMeta(title="demo", thumbnail=thumb)

    with pytest.raises(ThumbnailError) as excinfo:
        uploader.upload_video(video, meta, config_dir=tmp_path)

    assert excinfo.value.video_id == "video-123"
    assert "video-123" in str(excinfo.value)
