# soundstage

把音檔（鋼琴或任何錄音）合成影片，並上傳到 YouTube 的 CLI 工具。

## 前置需求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- **ffmpeg**（render 的核心，必須先裝好、在 PATH 上）：

  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu / Debian
  sudo apt install ffmpeg

  # Windows
  winget install ffmpeg
  ```

## 安裝

```bash
git clone https://github.com/joechiboo/soundstage.git
cd soundstage
uv sync
```

之後用 `uv run soundstage ...` 執行，或 `uv tool install .` 裝成全域指令。

## 快速開始

```bash
# 音檔 + 封面圖 → mp4
uv run soundstage render input.wav --cover cover.jpg -o out.mp4

# 沒有封面圖也可以：自動用純色背景 + 檔名文字
uv run soundstage render input.wav

# 除錯時看實際執行的 ffmpeg 指令
uv run soundstage render input.wav -v
```

其他選項：`--width` / `--height`（預設 1920×1080）、`--fps`（預設 30）。

## metadata 設定檔

`upload` / `publish` 用 yaml（或 json）管理影片資訊，範例見
[`examples/meta.yaml`](examples/meta.yaml)：

```yaml
title: 月光奏鳴曲 第一樂章
description: |
  鋼琴練習錄音。
tags: [piano, beethoven, 古典樂]
privacy: unlisted   # private / unlisted / public，預設 private
thumbnail: cover.jpg  # 相對路徑以設定檔所在目錄為準（可省略）
```

## 上傳到 YouTube（開發中）

```bash
uv run soundstage upload out.mp4 --meta meta.yaml
uv run soundstage publish input.wav --meta meta.yaml   # render + upload 一次做完
```

`upload` 目前是 stub，執行會提示尚未實作；規劃為 YouTube Data API v3 +
OAuth 2.0（token 快取在 `~/.config/soundstage/`），細節見
`src/soundstage/upload/uploader.py` 的 TODO。`publish` 的 render 部分已可用。

## 開發

```bash
uv sync
uv run pytest
```

專案結構：

```
src/soundstage/
├── cli.py        # typer CLI，只做參數解析與錯誤呈現
├── errors.py     # 共用例外
├── render/       # 音檔 + 封面 → mp4（ffmpeg subprocess）
│   ├── spec.py       # RenderSpec / VisualStyle 型別
│   ├── ffmpeg.py     # 純函式組裝 ffmpeg 指令，可單獨測試
│   ├── cover.py      # 預設封面（純色背景 + 檔名）
│   └── renderer.py   # render 流程
├── meta/         # VideoMeta 型別 + yaml/json 載入
└── upload/       # YouTube 上傳（stub）
```

模組之間只透過各自 `__init__.py` 匯出的型別與函式溝通。視覺化樣式
（波形、頻譜）是預留的擴充點：在 `render/ffmpeg.py` 的
`_COMMAND_BUILDERS` 註冊新的指令組裝函式即可。

## Roadmap

- [x] render：靜態封面
- [ ] upload：YouTube Data API v3 + OAuth 2.0
- [ ] render：波形視覺化（ffmpeg `showwaves`）
- [ ] render：頻譜視覺化（ffmpeg `showspectrum`）
