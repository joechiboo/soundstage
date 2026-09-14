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

# 輸入也可以是影片檔（例如手機錄的演奏影片），只取其中的音訊軌
uv run soundstage render recording.mp4 --cover cover.jpg -o out.mp4

# 波形視覺化：整首的波形圖 + 隨音樂移動的播放頭
uv run soundstage render input.wav --visual waveform --cover cover.jpg -o out.mp4

# 除錯時看實際執行的 ffmpeg 指令
uv run soundstage render input.wav -v
```

其他選項：`--width` / `--height`（預設 1920×1080）、`--fps`（預設 30）、
`--visual`（`static` 靜態封面，預設／`waveform` 波形）。`publish` 也吃 `--visual`。

`waveform` 會把封面當背景，在下三分之一疊上整首的波形圖，加一條隨音樂移動的
播放頭，中央留給封面本身的標題。
解析度必須是偶數，這是 H.264 的限制。

輸入可以是任何 ffmpeg 讀得懂的音訊或影片檔。影像一律取自封面圖，
輸入檔自己夾帶的畫面（影片的視訊軌、mp3 的內嵌專輯封面）都會被忽略。

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

## 上傳到 YouTube

上傳功能的相依套件是選用的，要先裝起來：

```bash
uv sync --extra upload
```

### 一次性設定：Google OAuth 憑證

**完整步驟（含檢查點與疑難排解）見 [docs/youtube-setup.md](docs/youtube-setup.md)。**

摘要：

1. 到 [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   建立（或選擇）一個專案
2. 啟用 **YouTube Data API v3**
3. 在「Google Auth Platform」設定：**品牌**（應用程式名稱）、**資料存取權**
   （加入 `youtube.upload` 範圍）、**目標對象**（把自己加進測試使用者；發布狀態
   留在「測試」即可，代價只是 refresh token 每 7 天要重跑一次 `auth`）
4. **用戶端** → 建立用戶端 → 應用程式類型選 **電腦版應用程式**（Desktop app）
5. 下載 JSON，存成 `~/.config/soundstage/client_secret.json`
   （或設 `SOUNDSTAGE_CLIENT_SECRET` 環境變數指向任意路徑）

接著跑一次授權，瀏覽器登入後 token 會快取到
`~/.config/soundstage/token.json`（權限 0600），之後不用再登入：

```bash
uv run soundstage auth              # 開瀏覽器完成授權
uv run soundstage auth --status     # 查看憑證與 token 狀態
uv run soundstage auth --reset      # 清除 token，下次重新授權
uv run soundstage auth --no-browser # 遠端主機：改在終端機顯示授權網址
```

token 過期會自動用 refresh token 更新；若授權被撤銷，會自動重跑一次授權流程。

⚠️ **Windows 上 0600 不生效**：Windows 不實作 POSIX 權限位元，`chmod` 只認唯讀
旗標，token 檔實際落地是 0666。實務上靠 `%USERPROFILE%` 自己的 ACL 擋住其他
一般使用者，但這是繼承來的保護，不是本工具做的。細節見 TODO.md 的 D 項。

### 上傳

```bash
# 上傳現成的影片
uv run soundstage upload out.mp4 --meta meta.yaml

# render + upload 一次做完
uv run soundstage publish input.wav --meta meta.yaml --cover cover.jpg

# 臨時覆蓋設定檔裡的公開狀態
uv run soundstage upload out.mp4 --meta meta.yaml --privacy public
```

- 用 resumable upload，中途遇到 5xx 或連線中斷會自動退避重試（最多 5 次）
- 終端機下會顯示上傳進度百分比
- `meta.thumbnail` 有設定時會在上傳後套用縮圖；縮圖失敗不影響影片，
  訊息會附上影片網址提醒不需要重傳
- `publish` 會**先驗證 metadata 再 render**，避免花時間編碼完才發現設定檔有問題

### 配額提醒

YouTube Data API 每日預設配額 10,000 點，上傳一支影片約耗 **1,600 點**，
也就是一天大約只能傳 6 支。超過會收到 HTTP 403 `quotaExceeded`，
隔日（太平洋時間午夜）重置。

## 開發

```bash
uv sync --extra upload   # 含上傳相依，才能跑到 OAuth 相關測試
uv run pytest
```

測試不會碰網路：OAuth 與 YouTube API 都用假的 client 替換，
`build_render_command()` / `build_video_body()` 是純函式可直接驗證輸出。
只跑 `uv sync`（沒有 extra）時，render 一切正常，upload 會提示缺少套件。

專案結構：

```
src/soundstage/
├── cli.py        # typer CLI，只做參數解析與錯誤呈現
├── errors.py     # 共用例外
├── render/       # 音檔 + 封面 → mp4（ffmpeg subprocess）
│   ├── spec.py       # RenderSpec / VisualStyle 型別
│   ├── ffmpeg.py     # 純函式組裝 ffmpeg 指令，可單獨測試
│   ├── probe.py      # 用 ffprobe 探測輸入（音訊長度）
│   ├── cover.py      # 預設封面（純色背景 + 檔名）
│   └── renderer.py   # render 流程
├── meta/         # VideoMeta 型別 + yaml/json 載入
└── upload/       # YouTube 上傳
    ├── auth.py       # OAuth 2.0 流程與 token 快取
    ├── youtube.py    # request body 組裝（純函式）+ resumable upload
    └── uploader.py   # upload 流程
```

模組之間只透過各自 `__init__.py` 匯出的型別與函式溝通。視覺化樣式
（波形、頻譜）是預留的擴充點：在 `render/ffmpeg.py` 的
`_COMMAND_BUILDERS` 註冊新的指令組裝函式即可。

## Roadmap

- [x] render：靜態封面
- [x] upload：YouTube Data API v3 + OAuth 2.0
- [x] render：波形視覺化（ffmpeg `showwavespic` + 播放頭）
- [ ] render：頻譜視覺化（ffmpeg `showspectrum`）
