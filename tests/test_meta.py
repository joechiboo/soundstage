import pytest

from soundstage.errors import InputFileError, MetaError
from soundstage.meta import Privacy, load_meta


def test_load_yaml(tmp_path):
    path = tmp_path / "meta.yaml"
    path.write_text(
        "title: 月光奏鳴曲\n"
        "description: 練習錄音\n"
        "tags: [piano, beethoven]\n"
        "privacy: unlisted\n",
        encoding="utf-8",
    )
    meta = load_meta(path)
    assert meta.title == "月光奏鳴曲"
    assert meta.tags == ["piano", "beethoven"]
    assert meta.privacy is Privacy.UNLISTED


def test_load_json(tmp_path):
    path = tmp_path / "meta.json"
    path.write_text('{"title": "demo"}', encoding="utf-8")
    meta = load_meta(path)
    assert meta.title == "demo"
    assert meta.privacy is Privacy.PRIVATE  # 預設 private


def test_thumbnail_resolved_relative_to_config(tmp_path):
    path = tmp_path / "meta.yaml"
    path.write_text("title: demo\nthumbnail: thumb.jpg\n", encoding="utf-8")
    meta = load_meta(path)
    assert meta.thumbnail == (tmp_path / "thumb.jpg").resolve()


def test_missing_file(tmp_path):
    with pytest.raises(InputFileError, match="找不到"):
        load_meta(tmp_path / "nope.yaml")


def test_missing_title(tmp_path):
    path = tmp_path / "meta.yaml"
    path.write_text("description: no title\n", encoding="utf-8")
    with pytest.raises(MetaError, match="title"):
        load_meta(path)


def test_bad_privacy(tmp_path):
    path = tmp_path / "meta.yaml"
    path.write_text("title: demo\nprivacy: everyone\n", encoding="utf-8")
    with pytest.raises(MetaError, match="privacy"):
        load_meta(path)


def test_unsupported_suffix(tmp_path):
    path = tmp_path / "meta.toml"
    path.write_text('title = "demo"', encoding="utf-8")
    with pytest.raises(MetaError, match="不支援"):
        load_meta(path)


def test_broken_yaml(tmp_path):
    path = tmp_path / "meta.yaml"
    path.write_text("title: [unclosed", encoding="utf-8")
    with pytest.raises(MetaError, match="解析失敗"):
        load_meta(path)
