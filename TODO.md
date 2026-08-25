# TODO

接手前先看這份。最後更新：2026-08-25。

---

## 開發環境現況（joechiboo 的 Windows 機器）

| 工具 | 版本 | 位置 |
|---|---|---|
| uv | 0.12.5 | `C:\Users\joechiboo\.local\bin` |
| ffmpeg / ffprobe | N-126262 (BtbN GPL build) | `C:\ffmpeg\bin` |
| Python | 3.14.3 | `C:\Python314` |

兩個路徑都已寫進 User PATH，**新開的 shell** 才生效。舊 shell 裡跑測試會踩到下面的 B 項。

⚠️ README 寫的 `winget install ffmpeg` 在這台機器行不通（沒有 winget）。
gyan.dev 的 `ffmpeg-release-essentials.zip` 下載會卡死（實測 10 分鐘 0 bytes），
改用 GitHub 的 BtbN build 才順（162 MB / 8 秒）：

```
https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
```

---

## A. render 的 `-shortest` 溢出 2.28 秒 🔴

**症狀**：輸出影片比音訊長 2.28 秒（68 格），尾巴多出一段無聲的封面畫面，
而終端機照樣顯示「已輸出影片」——又是一個靜默的錯誤輸出，
性質跟先前修掉的 `-map` bug 同型。

用真實檔案實測（2:28 的手機錄影）：

| 串流 | 長度 |
|---|---|
| 輸入音訊 | 147.752s |
| 輸出音訊 | 147.752s ✅ |
| 輸出影像 | **150.033s**（4501 格）❌ |

**三個解法實測結果**：

| 做法 | 結果 |
|---|---|
| `-fflags +shortest` | 這版 ffmpeg 已移除此 flag，直接報錯寫不出檔案 |
| `-shortest_buf_duration 0.05` | 無效，150.100s（還略差） |
| `-t <音訊實際長度>` | **有效**，147.767s vs 147.752s，差 14 ms（不到 30fps 的半格） |

**要改的地方**：`-t` 需要先知道音訊長度，而 `render/ffmpeg.py` 目前刻意維持
「只組 argv、不跑 subprocess」的純函式設計（見該檔 docstring）。所以動作是：

1. 新增 probe：`ffprobe -v error -show_entries stream=duration -select_streams a:0`
2. `RenderSpec` 加一個 duration 欄位
3. `_build_static_command()` 用 `-t {duration}` 取代 `-shortest`
4. 補測試：純函式那層驗 argv 有 `-t`，整合測試那層驗輸出長度

專案目前完全沒用過 ffprobe，這會是第一處。

---

## B. `test_odd_dimensions_rejected` 會因環境而失敗 🟡

**症狀**：機器上沒有 ffmpeg 時，`tests/test_render.py` 的
`test_odd_dimensions_rejected[1921-1080]` 和 `[1920-1081]` 兩個測試會失敗。
有 ffmpeg 時才過。也就是說這個測試在驗的東西跟它以為在驗的不一樣。

**根因**：`render/renderer.py` 的檢查順序。

```python
if shutil.which("ffmpeg") is None:      # L46-47：先擋 ffmpeg
    raise FFmpegNotFoundError()

with tempfile.TemporaryDirectory(...):
    # 先決定封面路徑並建好 spec，讓參數錯誤在做任何實際工作之前就浮現
    spec = RenderSpec(...)              # L53：尺寸驗證在這裡才發生
```

L50 的註解講的正是「參數錯誤要最先浮現」，但實際順序違反了它。
連帶的使用者體驗問題：沒裝 ffmpeg 的人打錯解析度，會被告知「找不到 ffmpeg」，
修好 ffmpeg 之後才發現真正的錯是尺寸是奇數。

**建議修法**：把 L46-47 的 ffmpeg 檢查移到 `RenderSpec` 建好之後、
`make_fallback_cover()` 之前。參數驗證不該需要裝 ffmpeg 才能跑。
改完那兩個測試在有無 ffmpeg 的機器上都會過。

（對照：`tests/test_render.py:76` 的整合測試有正確用 skip 標記擋掉，
這兩個沒有——因為它們原本就不該需要 ffmpeg。）

---

## C. upload 的真實路徑從未驗證過 🔴

目前 `~/.config/soundstage/` **不存在**，代表 OAuth 從來沒實際跑過一次。

測試裡的 OAuth 與 YouTube API 全是假 client（這是對的，測試不該碰網路），
但也代表以下路徑一次都沒被真實執行過：

- `soundstage auth` 開瀏覽器、拿 token、寫進 `token.json`（權限 0600）
- token 過期後用 refresh token 自動更新
- 授權被撤銷時自動重跑授權流程
- resumable upload 遇到 5xx / 斷線的退避重試
- 上傳後套用 `meta.thumbnail` 縮圖
- 配額用盡的 403 `quotaExceeded` 處理

**第一次實跑前要先做的事**（README「上傳到 YouTube」段有完整步驟）：

1. Google Cloud Console 建專案、啟用 YouTube Data API v3
2. 建 OAuth 用戶端 ID（桌面應用程式），下載 JSON
3. 存成 `~/.config/soundstage/client_secret.json`
4. `uv sync --extra upload`（上傳相依是選用的，預設沒裝）
5. `uv run soundstage auth`

⚠️ 第一次實測請用 `privacy: private`，別直接 public。
⚠️ 每日配額 10,000 點，一支影片約 1,600 點 → 一天約 6 支，測試時省著用。

---

## D. 首支實際作品：《菊次郎の夏》

《夜曲 No.9-2》已經在作品集裡了，所以改用最近在練的《菊次郎の夏》當第一支。
**等錄音練完才推進**。

現況：
- render 這條線已用真實檔案驗證過（見下方「已驗證」），可以直接用
- 還缺**真正的封面圖**——目前只用程式生的純色測試圖驗證過
- 建議順序：練完 → 錄音 → 做封面 → render → 先 private 上傳試一次 → 改 unlisted/public

---

## E. Roadmap（README 既有項目）

- [ ] render：波形視覺化（ffmpeg `showwaves`）
- [ ] render：頻譜視覺化（ffmpeg `showspectrum`）

擴充點在 `render/ffmpeg.py` 的 `_COMMAND_BUILDERS`，註冊新的指令組裝函式即可。

**做這兩項時會踩到的坑**：手機錄的直式影片帶有 `rotation=-90` 的顯示矩陣
（實測檔案就是，ffprobe 報 1920×1080 但解碼出來是 1080×1920 直式）。
目前靜態封面路徑整路忽略輸入的影像軌，所以不受影響；
但若之後做「波形疊在原片畫面上」這類功能，就必須處理旋轉。

---

## 已驗證，不用重做

2026-08-25 用真實檔案（304 MB、2:28、h264 1920×1080 rotation=-90、
AAC 48kHz 立體聲 256kbps 的手機錄影）跑過：

- **`-map` 修正成立**。刻意配一張比影片小的 720p 封面（就是舊版會靜默出錯的組合），
  輸出在 5s / 74s / 145s 三個時間點抽格，畫面全部是純封面色 `(68,127,178)`；
  同一秒的原始影片有 39,834 種顏色。對照組成立。
- **音訊完整**。輸出與來源的左右聲道 RMS 相差 0.01 dB 以內，不是靜音。
- **效能**：2:28 的素材 render 耗時 17.4 秒，輸出 3.8 MB。
- **影片檔可直接當輸入**，會取音訊軌、忽略影像軌，如 README 所述。

（附帶觀察：那份原始錄音的峰值是 +0.09 dBFS，已經削頂。
不影響工具本身，但要發布的話錄音端值得注意。）
