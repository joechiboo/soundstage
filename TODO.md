# TODO

接手前先看這份。最後更新：2026-09-14。

---

## 開發環境現況（joechiboo 的 Windows 機器）

| 工具 | 版本 | 位置 |
|---|---|---|
| uv | 0.12.5 | `C:\Users\joechiboo\.local\bin` |
| ffmpeg / ffprobe | N-126262 (BtbN GPL build) | `C:\ffmpeg\bin` |
| Python | 3.14.3 | `C:\Python314` |

兩個路徑都已寫進 User PATH。`uv sync --extra upload` 已經裝好（上傳相依是選用的）。

⚠️ README 寫的 `winget install ffmpeg` 在這台機器行不通（沒有 winget）。
gyan.dev 的 `ffmpeg-release-essentials.zip` 下載會卡死（實測 10 分鐘 0 bytes），
改用 GitHub 的 BtbN build 才順（162 MB / 8 秒）：

```
https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
```

⚠️ 用 `python - <<'EOF'` 這種 heredoc 改檔時，字串裡的 `\n` 會被吃掉一層反斜線，
Python 收到的是真正的換行。做字串比對時錨點請避開含跳脫字元的行。

---

## C. upload 的真實路徑仍未驗證過 🔴

**目前唯一擋住「render + 上傳」全流程的東西。**

**2026-09-14 進度**：OAuth 授權本身已經實跑成功一次。專案 `YoutubeUploader`
建好、範圍與測試使用者設定完成、`soundstage auth` 跑通，`token.json` 拿到了
正確的 scope 與 refresh token。

測試裡的 OAuth 與 YouTube API 仍全是假 client（這是對的，測試不該碰網路），
以下路徑**還是一次都沒被真實執行過**：

- ~~`soundstage auth` 開瀏覽器、拿 token、寫進 `token.json`~~ ✅
- ~~實際上傳一支影片（resumable upload + metadata）~~ ✅
  2026-09-14 傳出第一支：`https://youtu.be/bbVbvxobK-s`，1.03 MB / 7 秒 / private
- token 過期後用 refresh token 自動更新（要等超過 1 小時才驗得到）
- 測試模式 7 天期限到了自動重跑授權流程（2026-09-21 之後才驗得到）
- resumable upload 遇到 5xx / 斷線的退避重試（難以自然觸發）
- 上傳後套用 `meta.thumbnail` 縮圖（meta.yaml 目前沒設 thumbnail，沒走到）
- 配額用盡的 403 `quotaExceeded` 處理
- **影片能不能真的改成 public**——未通過 API 稽核的專案可能被鎖在 private。
  第一支本來就設 private，所以還沒驗到；要在 Studio 手動改成 unlisted 試試看

⚠️ 回查驗證做不到：我們只申請 `youtube.upload` 範圍，沒有讀取權，
`videos.list` 會回 403 `insufficientPermissions`。這是對的（最小權限），
要確認上傳結果只能去 YouTube Studio 看。

**第一次實跑前要做的事**：完整步驟見 [docs/youtube-setup.md](docs/youtube-setup.md)。
只有帳號擁有者能做，全部在瀏覽器裡。重點是別漏掉「把自己加進測試使用者」
和「發布狀態改成正式版」這兩步——後者不做的話 refresh token 只活 7 天。

⚠️ 第一次實測請用 `privacy: private`，別直接 public。
⚠️ 每日配額 10,000 點，一支影片約 1,600 點 → 一天約 6 支，測試時省著用。

---

## D. Windows 上 token 檔的權限保護是空的 🟡

`upload/auth.py` 的 `save_credentials()` 寫著「權限設為 0600（只有自己讀得到）」，
README 也這樣宣稱，但 **Windows 不實作 POSIX 權限位元**，`path.chmod(0o600)`
是無效操作。實測 `token.json` 落地是 `0o666`。

實務風險不高——`%USERPROFILE%` 自己的 ACL 已經擋住其他一般使用者——但那是
繼承來的，不是這段程式做的事，而程式與文件都宣稱做了。

相關的次要問題：`write_text()` 先寫檔、`chmod()` 後設權限，POSIX 上中間有一個
短暫的視窗檔案是預設權限。要修的話一起處理：用 `os.open(..., 0o600)` 建檔。

`tests/test_upload_auth.py::test_save_credentials_is_private` 目前在 Windows 上
標了 `xfail(strict=True)`，POSIX 照常驗。真的修好之後記得把那個標記拿掉
（strict 會讓它意外通過時報錯，不會被忘記）。

修法方向：Windows 走 `icacls`（移除繼承、只給目前使用者），或改用 `%APPDATA%`
搭配明確的 ACL。

---

## E. 首支實際作品：《菊次郎の夏》

《夜曲 No.9-2》已經在作品集裡了，所以改用《菊次郎の夏》當第一支。

**目前卡在錄音品質，還不能發。** 2026-09-14 收到的 `voice_295093.aac`：

| | 這個檔 | 之前那支手機錄影 |
|---|---|---|
| 取樣率 | **16 kHz** | 48 kHz |
| 聲道 | **單聲道** | 立體聲 |
| 位元率 | **16.4 kbps** | 256 kbps |
| 長度 | 62.2 秒 | 147.8 秒 |

頻譜實測：**5 kHz 以上完全是空的**（編碼器砍的，比 16 kHz 取樣的 8 kHz
理論上限還低）。各頻段 RMS：

```
  20–500 Hz   -17.6 dB
 500–2000 Hz  -22.7 dB
2000–4000 Hz  -35.5 dB
4000–6000 Hz  -47.3 dB   ← 開始掉崖
6000–7800 Hz  -61.9 dB   ← 幾乎是空的
```

鋼琴最高音 C8 基頻 4186 Hz，所以音高還在；但決定亮度與琴槌觸鍵質感的泛音
幾乎全在 5 kHz 以上，全沒了。這是語音備忘錄規格，不是音樂錄音。

**建議用相機 App 重錄**（同一支手機上次就錄出 48 kHz 立體聲 256 kbps）。

還缺**真正的封面圖**——目前跑 render 會用預設封面，產出的是深藍底加白字
`voice_295093`，不能當作品集封面。

---

## F. Roadmap（README 既有項目）

- [x] render：波形視覺化 — 見下方「已完成」
- [ ] render：頻譜視覺化（ffmpeg `showspectrum`）

擴充點在 `render/ffmpeg.py` 的 `_COMMAND_BUILDERS`，註冊新的指令組裝函式即可。

⚠️ 頻譜視覺化要注意：目前這份 16 kHz 的錄音 5 kHz 以上是空的，頻譜圖會把
那片死區直接畫給觀眾看，等於公開展示錄音品質不足。重錄之前別做這個。

**做頻譜時會踩到的坑**：手機錄的直式影片帶有 `rotation=-90` 的顯示矩陣
（實測檔案就是，ffprobe 報 1920×1080 但解碼出來是 1080×1920 直式）。
目前靜態封面路徑整路忽略輸入的影像軌，所以不受影響；
但若之後做「波形疊在原片畫面上」這類功能，就必須處理旋轉。

---

## 已完成

### F（部分）波形視覺化 ✅ 2026-09-14

`VisualStyle.WAVEFORM`，CLI 走 `--visual waveform`（`render` 與 `publish` 都吃）。

刻意用 `showwavespic`（整首一張靜態波形 + 移動播放頭）而不是 `showwaves`
（示波器）：`showwaves` 每格只畫 1/fps 秒的音訊，16 kHz 在 30fps 下只有 533 個
取樣要鋪滿 1920 像素，畫面填不滿；而且每格只看得到 33 毫秒，讀不出樂曲結構。

**兩個踩了很久的坑，都已經寫成測試釘住：**

1. **`blend` 一定要在 RGB 平面上做。** 走預設的 YUV 時，`screen` 會被套到色度
   平面上，整個畫面變成洋紅色——而 ffmpeg 完全不報錯，輸出照樣「成功」。
   兩路輸入進 `blend` 前都要 `format=gbrp`。

2. **播放頭只能用 `overlay`，不能用 `drawbox`。** `drawbox` 的運算式裡 `t` 是
   「線寬」不是時間，`n` 根本沒定義。拿 `t` 當時間會算出畫面外的座標，box 就
   無聲無息地消失，同樣不報錯。`overlay` 才有 `t` / `n` 時間變數，所以播放頭
   是一路獨立的 `lavfi` 白色長條輸入。

順帶一提，`showwavespic` 的底色是黑的，`screen` 混合時黑色不改變背景，等於
免費去背，不需要 colorkey。

### A. `-shortest` 溢出 ✅ 2026-09-14

輸出影像軌會比音訊長約 2 秒（兩支素材分別是 2.06s 與 2.28s），尾巴多一段
無聲畫面而 ffmpeg 照樣回報成功——與先前的 `-map` bug 同型的靜默錯誤輸出。

修法：新增 `render/probe.py` 用 ffprobe 探測音訊長度，`RenderSpec` 帶
`duration` 欄位，指令改用 `-t`。`-fflags +shortest` 在新版 ffmpeg 已移除，
`-shortest_buf_duration` 實測無效。

⚠️ 關鍵細節：`-t` 必須比音訊長度**多一點**（`_DURATION_EPSILON = 0.25`）。
切在正好的長度上，音訊編碼器會少輸出最後一格——實測 16 kHz 的 AAC 少 64 ms，
等於把 2 秒的靜默溢出換成 64 毫秒的靜默截斷。多出來的部分由 `-shortest` 收掉。

實測結果（兩支真實素材，音訊完整、影像不到一格的誤差）：

| 素材 | 輸出音訊 | 輸出影像 |
|---|---|---|
| voice_295093.aac (62.208s) | +0.000s | −0.008s |
| 手機錄影 (147.752s) | +0.000s | −0.019s |

另外：探測一律用**音訊軌自己的** duration，不能用容器的 format duration。
影片檔的容器長度是以較長的串流為準，實測差 31 ms。

### B. 測試會因環境有沒有 ffmpeg 而失敗 ✅ 2026-09-14

`renderer.py` 的 ffmpeg 存在檢查排在 `RenderSpec` 尺寸驗證之前，導致沒裝
ffmpeg 的機器上 `test_odd_dimensions_rejected` 必定失敗，且使用者打錯解析度
會先被叫去裝 ffmpeg。已把檢查移到 spec 建好之後，並加了 monkeypatch
`shutil.which` 的測試把順序釘死。

驗證：把 `C:\ffmpeg\bin` 移出 PATH 跑整套 → 47 passed / 0 failed
（修正前同樣條件是 2 failed）。

### `-map` 修正的真實檔案驗證 ✅ 2026-08-25

用 304 MB、2:28、h264 1920×1080 rotation=-90、AAC 48kHz 立體聲 256kbps 的
手機錄影跑過：

- 刻意配一張比影片小的 720p 封面（舊版會靜默出錯的組合），輸出在 5s / 74s /
  145s 三個時間點抽格，畫面全部是純封面色；同一秒的原始影片有 39,834 種顏色。
- 音訊完整，輸出與來源左右聲道 RMS 相差 0.01 dB 以內。
- 2:28 的素材 render 耗時 17.4 秒，輸出 3.8 MB。
