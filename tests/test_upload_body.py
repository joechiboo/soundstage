"""build_video_body 是純函式，不需要 Google 套件也能測。"""

from soundstage.meta import Privacy, VideoMeta
from soundstage.upload import build_video_body


def make_meta(**overrides) -> VideoMeta:
    return VideoMeta(**{"title": "月光奏鳴曲", **overrides})


def test_body_maps_meta_fields():
    meta = make_meta(description="練習錄音", tags=["piano", "beethoven"])
    body = build_video_body(meta)

    assert body["snippet"]["title"] == "月光奏鳴曲"
    assert body["snippet"]["description"] == "練習錄音"
    assert body["snippet"]["tags"] == ["piano", "beethoven"]
    assert body["snippet"]["categoryId"] == "10"


def test_body_defaults_to_private():
    assert build_video_body(make_meta())["status"]["privacyStatus"] == "private"


def test_privacy_argument_overrides_meta():
    meta = make_meta(privacy=Privacy.PRIVATE)
    body = build_video_body(meta, Privacy.PUBLIC)
    assert body["status"]["privacyStatus"] == "public"


def test_none_privacy_keeps_meta_value():
    meta = make_meta(privacy=Privacy.UNLISTED)
    body = build_video_body(meta, None)
    assert body["status"]["privacyStatus"] == "unlisted"


def test_tags_are_copied_not_aliased():
    meta = make_meta(tags=["piano"])
    body = build_video_body(meta)
    body["snippet"]["tags"].append("mutated")
    assert meta.tags == ["piano"]


def test_made_for_kids_declared():
    # YouTube 要求明確宣告，漏掉會被 API 退件
    assert build_video_body(make_meta())["status"]["selfDeclaredMadeForKids"] is False
