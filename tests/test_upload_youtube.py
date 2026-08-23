"""upload_video_file 的重試與錯誤訊息，用假的 API client 測。"""

import pytest

from soundstage.errors import UploadError
from soundstage.upload import youtube


class FakeResp:
    def __init__(self, status):
        self.status = status


class FakeHttpError(Exception):
    def __init__(self, status, reason="boom"):
        self.resp = FakeResp(status)
        self.reason = reason
        super().__init__(reason)


class FakeStatus:
    def __init__(self, fraction):
        self._fraction = fraction

    def progress(self):
        return self._fraction


class FakeRequest:
    """依照 script 逐次回應：例外類別代表拋錯，tuple 代表正常回傳。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def next_chunk(self):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


@pytest.fixture
def fake_api(monkeypatch):
    """讓 youtube 模組拿到假的 build / HttpError / MediaFileUpload。"""
    state = {}

    def install(request):
        state["request"] = request

        class FakeVideos:
            def insert(self, **kwargs):
                state["insert_kwargs"] = kwargs
                return request

        class FakeThumbnails:
            def set(self, **kwargs):
                state["thumbnail_kwargs"] = kwargs
                return self

            def execute(self):
                return {}

        class FakeYouTube:
            def videos(self):
                return FakeVideos()

            def thumbnails(self):
                return FakeThumbnails()

        def fake_build(*args, **kwargs):
            return FakeYouTube()

        monkeypatch.setattr(
            youtube,
            "_import_google",
            lambda: (fake_build, FakeHttpError, lambda path, **kw: f"media:{path}"),
        )
        return state

    return install


def test_upload_reports_progress_and_id(fake_api):
    request = FakeRequest([(FakeStatus(0.5), None), (None, {"id": "abc123"})])
    fake_api(request)

    seen = []
    video_id = youtube.upload_video_file(
        "creds", "video.mp4", {"snippet": {}}, on_progress=seen.append
    )

    assert video_id == "abc123"
    assert seen == [0.5, 1.0]  # 結束時補一次 100%


def test_retries_transient_error(fake_api):
    request = FakeRequest([FakeHttpError(503), (None, {"id": "abc123"})])
    fake_api(request)

    slept = []
    video_id = youtube.upload_video_file(
        "creds", "video.mp4", {}, sleep=slept.append
    )

    assert video_id == "abc123"
    assert request.calls == 2
    assert slept == [2]  # 第一次退避 2 秒


def test_gives_up_after_max_retries(fake_api):
    request = FakeRequest([FakeHttpError(500)] * (youtube.MAX_RETRIES + 1))
    fake_api(request)

    with pytest.raises(UploadError, match="HTTP 500"):
        youtube.upload_video_file("creds", "video.mp4", {}, sleep=lambda _: None)

    assert request.calls == youtube.MAX_RETRIES + 1


def test_permanent_error_not_retried(fake_api):
    request = FakeRequest([FakeHttpError(403, "quotaExceeded")])
    fake_api(request)

    with pytest.raises(UploadError, match="配額"):
        youtube.upload_video_file("creds", "video.mp4", {}, sleep=lambda _: None)

    assert request.calls == 1  # 403 重試沒有意義


def test_missing_id_in_response(fake_api):
    fake_api(FakeRequest([(None, {"kind": "youtube#video"})]))

    with pytest.raises(UploadError, match="沒有回傳影片 ID"):
        youtube.upload_video_file("creds", "video.mp4", {})


def test_insert_uses_resumable_media(fake_api):
    state = fake_api(FakeRequest([(None, {"id": "abc"})]))
    youtube.upload_video_file("creds", "video.mp4", {"snippet": {"title": "x"}})

    kwargs = state["insert_kwargs"]
    assert kwargs["part"] == "snippet,status"
    assert kwargs["body"] == {"snippet": {"title": "x"}}
    assert kwargs["media_body"] == "media:video.mp4"


def test_describe_http_error_mentions_reauth():
    assert "重新授權" in youtube.describe_http_error(FakeHttpError(401))


def test_describe_http_error_unknown_status():
    message = youtube.describe_http_error(FakeHttpError(418, "teapot"))
    assert "418" in message and "teapot" in message
