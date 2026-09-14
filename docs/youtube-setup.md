# YouTube 上傳設定

一次性設定，約 10 分鐘。步驟 1–5 全部要在瀏覽器裡用你自己的 Google 帳號做，
沒有 CLI 的替代做法。

每做完一步都可以跑這行確認進度：

```bash
uv run soundstage auth --status
```

還沒開始時它會顯示：

```
client secret：C:\Users\joechiboo\.config\soundstage\client_secret.json（不存在）
token 快取：  C:\Users\joechiboo\.config\soundstage\token.json（不存在）
```

---

## 步驟 1：建立專案並啟用 API

1. 開 [console.cloud.google.com](https://console.cloud.google.com/)
2. 左上角專案選單 → **新增專案** → 取個名字（例如 `soundstage`）→ 建立
3. 確認右上角已切換到這個新專案
4. 左側「**API 和服務**」→「**程式庫**」
5. 搜尋 **YouTube Data API v3** → 點進去 → **啟用**

✅ **檢查點**：「API 和服務」→「已啟用的 API」裡看得到 YouTube Data API v3

---

## 步驟 2：設定 OAuth 同意畫面

「API 和服務」→「**OAuth 同意畫面**」

1. User Type 選 **外部**（個人 Gmail 帳號只有這個選項）→ 建立
2. 填必填欄位：
   - 應用程式名稱：`soundstage`
   - 使用者支援電子郵件：你的 Gmail
   - 開發人員聯絡資訊：你的 Gmail
3. 「新增或移除範圍」→ 手動加入：
   ```
   https://www.googleapis.com/auth/youtube.upload
   ```
   這個範圍會被標示為「敏感」，正常。
4. **測試使用者**：把你自己的 Gmail 加進去

> ⚠️ 第 4 步漏掉的話，步驟 5 授權時會直接被擋下來，錯誤訊息不會告訴你原因是這個。

✅ **檢查點**：同意畫面的摘要頁看得到那個 scope，測試使用者列表裡有你的信箱

---

## 步驟 3：把發布狀態改成「正式版」

還在「OAuth 同意畫面」頁，找到 **發布狀態** → 點 **發布應用程式** → 確認。

**為什麼一定要做這步**：停在「測試中」狀態時，Google 規定 refresh token
**7 天後失效**，等於每週都要重新授權一次，自動化免談。改成正式版就沒有這個限制。

會不會需要 Google 驗證？`youtube.upload` 是敏感範圍，如果要給一般大眾用的確
要送驗證。但**自用不需要** —— 發布後你自己照樣能授權，只是每次會看到一個
「未驗證」的警告畫面，點進階就能繼續。

✅ **檢查點**：發布狀態顯示「**正式版**」

---

## 步驟 4：建立憑證

「API 和服務」→「**憑證**」→ 建立憑證 → **OAuth 用戶端 ID**

- 應用程式類型：**桌面應用程式** ← 必須是這個，選錯了 `run_local_server` 流程會失敗
- 名稱隨意

建立後點 **下載 JSON**。

---

## 步驟 5：把憑證放到定位

```bash
mkdir -p ~/.config/soundstage
mv ~/Downloads/client_secret_*.json ~/.config/soundstage/client_secret.json
```

Windows 上這個目錄是 `C:\Users\<你>\.config\soundstage`。

也可以放在別的地方，用環境變數指過去：

```bash
export SOUNDSTAGE_CLIENT_SECRET=/path/to/client_secret.json
```

✅ **檢查點**：`uv run soundstage auth --status` 的 client secret 那行不再是「不存在」

---

## 步驟 6：授權

```bash
uv sync --extra upload   # 上傳相依是選用的，沒裝過要先裝
uv run soundstage auth
```

會發生的事：

1. 瀏覽器自動開啟（遠端主機請加 `--no-browser`，改在終端機顯示網址）
2. 選你的 Google 帳號
3. 看到「**Google 尚未驗證這個應用程式**」
   → 點「**進階**」→「**前往 soundstage（不安全）**」
   這是你自己建的 app，正常現象
4. 勾選權限 → 繼續
5. 終端機顯示授權完成

✅ **檢查點**：`uv run soundstage auth --status` 兩行都不再是「不存在」

---

## 之後每次怎麼用

```bash
# render 完再上傳
uv run soundstage upload out.mp4 --meta meta.yaml

# 或一行做完
uv run soundstage publish "菊次郎の夏 Part I.aac" --meta meta.yaml --visual waveform
```

token 過期會自動用 refresh token 更新，不用再登入。
授權被撤銷（改密碼、手動移除授權）時會自動重跑一次授權流程。

---

## 已知限制

### 上傳的影片可能被強制鎖成 private

YouTube 對**未通過 API 稽核**的專案有這個限制：不管 `meta.yaml` 裡的 `privacy`
設什麼，上傳後影片都會是 private。

要解除得申請 YouTube API Services 稽核（要填表、說明用途、等審核）。

**實務上的繞法**：上傳後到 [YouTube Studio](https://studio.youtube.com/) 手動改
公開狀態 —— 那是可以改的。一年傳幾支的話，不值得為此去申請稽核。

### 每日配額

預設 10,000 點，**上傳一支影片約 1,600 點**，所以一天大約只能傳 6 支。
超過會收到 HTTP 403 `quotaExceeded`，太平洋時間午夜重置。

### Windows 上 token 檔沒有權限保護

`save_credentials()` 會呼叫 `chmod(0o600)`，但 Windows 不實作 POSIX 權限位元，
這是無效操作，實際落地是 `0o666`。實務上靠 `%USERPROFILE%` 自己的 ACL 擋住
其他一般使用者，但那是繼承來的保護。細節見 [TODO.md](../TODO.md) 的 D 項。

---

## 疑難排解

| 症狀 | 原因 |
|---|---|
| 授權時被擋，說沒有權限 | 步驟 2 的**測試使用者**沒加自己；或步驟 3 沒發布 |
| 每週都要重新授權 | 發布狀態還停在「測試中」，回步驟 3 |
| `找不到 OAuth client secret` | 步驟 5 的路徑或檔名不對，跑 `auth --status` 看它期待的位置 |
| `缺少 YouTube 上傳所需的套件` | 沒跑 `uv sync --extra upload` |
| `run_local_server` 卡住或失敗 | 步驟 4 的應用程式類型選錯，必須是**桌面應用程式** |
| 上傳成功但影片是 private | 見上方「已知限制」，到 Studio 手動改 |
| HTTP 403 `quotaExceeded` | 當天配額用完，隔天再試 |

想從頭來過：

```bash
uv run soundstage auth --reset   # 只清 token，client secret 保留
```

---

## ⚠️ 著作權提醒

《菊次郎の夏》是久石讓 1999 年的作品，仍在著作權保護期內。鋼琴翻彈上傳到
YouTube 大機率會被 Content ID 比對到 —— 通常不是下架，而是廣告收益歸權利方，
但也可能在部分國家被封鎖。

建議第一支先用 `privacy: private` 傳上去，看系統怎麼判定，再決定要不要公開。
`meta.yaml` 的預設值就是 `private`。
